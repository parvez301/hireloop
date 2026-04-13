import { useState, type KeyboardEvent } from 'react';

interface InputBarProps {
  disabled: boolean;
  onSend: (content: string) => void;
}

export function InputBar({ disabled, onSend }: InputBarProps) {
  const [value, setValue] = useState('');

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue('');
  }

  function handleKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="sticky bottom-0 border-t border-[#e3e2e0] bg-white pt-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
        placeholder="Tell your agent what to do…"
        rows={2}
        className="w-full resize-none rounded border border-[#e3e2e0] bg-[#fbfbfa] px-3 py-2 text-sm focus:border-[#2383e2] focus:outline-none"
      />
      <div className="mt-2 flex justify-end">
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="rounded bg-[#2383e2] px-4 py-1.5 text-sm text-white disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
