import type { ReactNode } from 'react';

type Props = {
  right?: ReactNode;
  middle?: ReactNode;
};

export function AppHeader({ right, middle }: Props) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-white">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-6">
        <a href="/" className="flex items-center gap-3">
          <span
            aria-hidden
            className="h-6 w-6 rounded-md"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          />
          <span className="text-[15px] font-semibold tracking-tight text-ink">
            HireLoop
          </span>
        </a>
        <div className="flex-1">{middle}</div>
        <div>{right}</div>
      </div>
    </header>
  );
}
