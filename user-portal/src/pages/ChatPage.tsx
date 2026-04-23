import { useCallback, useEffect, useState } from 'react';

import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { InputBar } from '../components/chat/InputBar';
import { MessageList } from '../components/chat/MessageList';
import { ApiError, api, type Conversation, type Message } from '../lib/api';

export default function ChatPage() {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trialExpired, setTrialExpired] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const list = await api.listConversations();
        let conv = list.data[0];
        if (!conv) {
          const created = await api.createConversation('Default');
          conv = created.data;
        }
        if (cancelled) return;
        setConversation(conv);
        const detail = await api.getConversation(conv.id);
        if (cancelled) return;
        setMessages(detail.data.messages);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.code === 'TRIAL_EXPIRED') {
          setTrialExpired(true);
        }
        setError((e as Error).message);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (content: string) => {
      if (!conversation) return;
      setPending(true);
      setError(null);

      const optimisticUser: Message = {
        id: `tmp-${crypto.randomUUID()}`,
        conversation_id: conversation.id,
        role: 'user',
        content,
        cards: null,
        metadata: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticUser]);

      try {
        await api.sendMessage(conversation.id, content);
        const detail = await api.getConversation(conversation.id);
        setMessages(detail.data.messages);
      } catch (e) {
        const err = e as Error;
        if (e instanceof ApiError && e.code === 'TRIAL_EXPIRED') {
          setTrialExpired(true);
        }
        setError(err.message);
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      } finally {
        setPending(false);
      }
    },
    [conversation],
  );

  const goToCheckout = async () => {
    try {
      const res = await api.startCheckout();
      window.location.href = res.data.url;
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <WorkspaceShell>
      <div className="flex min-h-[70vh] flex-col gap-4">
        {trialExpired && (
          <div
            role="alert"
            className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          >
            <p className="font-medium">Your trial has ended</p>
            <p className="mt-1 text-amber-900/90">
              Subscribe to keep using the assistant. You will be redirected to secure checkout.
            </p>
            <button
              type="button"
              className="mt-3 rounded-md bg-amber-900 px-3 py-1.5 text-white hover:bg-amber-800"
              onClick={() => void goToCheckout()}
            >
              Continue to checkout
            </button>
          </div>
        )}
        <MessageList messages={messages} />
        {error && <p className="text-sm text-red-600">Error: {error}</p>}
        <InputBar disabled={pending || !conversation || trialExpired} onSend={send} />
      </div>
    </WorkspaceShell>
  );
}
