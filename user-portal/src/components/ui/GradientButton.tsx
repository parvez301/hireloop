import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  shape?: 'pill' | 'card';
};

export function GradientButton({
  children,
  className = '',
  shape = 'pill',
  style,
  ...rest
}: Props) {
  const radius = shape === 'card' ? 'rounded-2xl' : 'rounded-full';
  return (
    <button
      {...rest}
      style={{
        backgroundImage:
          'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
        ...style,
      }}
      className={
        `inline-flex items-center justify-center ${radius} ` +
        'from-accent-teal via-accent-cobalt to-accent-violet ' +
        'px-6 py-3 text-base font-semibold text-white transition-all duration-150 ' +
        'shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),0_2px_6px_-2px_rgba(15,23,42,0.12),inset_0_1px_0_rgba(255,255,255,0.15)] ' +
        'hover:-translate-y-px hover:shadow-[0_22px_48px_-18px_rgba(124,58,237,0.6),0_2px_6px_-2px_rgba(15,23,42,0.14),inset_0_1px_0_rgba(255,255,255,0.18)] ' +
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 ' +
        'motion-reduce:transition-none motion-reduce:hover:translate-y-0 ' +
        className
      }
    >
      {children}
    </button>
  );
}
