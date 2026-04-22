import type { HTMLAttributes, ReactNode } from 'react';

type Props = HTMLAttributes<HTMLDivElement> & {
  header?: ReactNode;
  padding?: 'sm' | 'md' | 'lg';
  border?: boolean;
};

const PADDING: Record<NonNullable<Props['padding']>, string> = {
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export function SoftCard({
  header,
  padding = 'md',
  border = true,
  className = '',
  children,
  ...rest
}: Props) {
  const borderCls = border ? 'border border-[#ece9e2]' : '';
  return (
    <div
      {...rest}
      className={
        `rounded-3xl bg-white shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)] ${borderCls} ${className}`
      }
    >
      {header && (
        <div className="border-b border-line bg-[#faf9f6] rounded-t-3xl px-5 py-3 text-[11px] uppercase tracking-[0.18em] text-ink-3">
          {header}
        </div>
      )}
      <div className={PADDING[padding]}>{children}</div>
    </div>
  );
}
