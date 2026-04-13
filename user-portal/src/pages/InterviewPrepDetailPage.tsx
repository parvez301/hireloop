import { useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { FeedbackWidget } from '../components/shared/FeedbackWidget';
import { api, type InterviewPrep } from '../lib/api';

export default function InterviewPrepDetailPage({ id }: { id: string }) {
  const [prep, setPrep] = useState<InterviewPrep | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const r = await api.interviewPreps.get(id);
        if (!cancelled) setPrep(r.data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <AppShell>
        <p className="text-[#e03e3e]">{error}</p>
      </AppShell>
    );
  }
  if (!prep) {
    return (
      <AppShell>
        <p className="text-[#787774]">Loading…</p>
      </AppShell>
    );
  }

  const qs = prep.questions as Array<{
    question?: string;
    category?: string;
    framework?: string;
  }>;

  return (
    <AppShell>
      <a href="/interview-prep" className="text-sm text-[#2383e2] hover:underline">
        ← All interview prep
      </a>
      <h1 className="mt-2 text-xl font-semibold">
        {prep.custom_role || 'Job-specific prep'}
      </h1>
      <p className="text-xs text-[#787774]">{new Date(prep.created_at).toLocaleString()}</p>

      <section className="mt-6">
        <h2 className="text-sm font-semibold text-[#787774]">Likely questions</h2>
        <ol className="mt-2 list-decimal space-y-3 pl-5 text-sm">
          {qs.map((q, i) => (
            <li key={i}>
              <p>{q.question}</p>
              {q.framework && (
                <p className="text-xs text-[#787774]">Framework: {q.framework}</p>
              )}
            </li>
          ))}
        </ol>
      </section>

      {prep.red_flag_questions && prep.red_flag_questions.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-semibold text-[#787774]">Ask them</h2>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm">
            {(prep.red_flag_questions as Array<{ question?: string; what_to_listen_for?: string }>).map(
              (r, i) => (
                <li key={i}>
                  {r.question}
                  {r.what_to_listen_for && (
                    <span className="text-[#787774]"> — {r.what_to_listen_for}</span>
                  )}
                </li>
              ),
            )}
          </ul>
        </section>
      )}

      <FeedbackWidget resource="interview_prep" resourceId={prep.id} className="mt-8" />
    </AppShell>
  );
}
