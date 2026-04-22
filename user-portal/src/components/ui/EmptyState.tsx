import type { ReactNode } from 'react';

type Props = {
  title: string;
  body?: string;
  cta?: ReactNode;
};

export function EmptyState({ title, body, cta }: Props) {
  return (
    <div className="rounded-3xl border border-dashed border-line-2 bg-transparent p-8 text-center">
      <div className="text-[14px] font-medium text-ink">{title}</div>
      {body && <p className="mx-auto mt-1 max-w-sm text-[13px] text-ink-3">{body}</p>}
      {cta && <div className="mt-4 flex justify-center">{cta}</div>}
    </div>
  );
}
