import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

export function GradientButton({ children, className = '', ...rest }: Props) {
  return (
    <button
      {...rest}
      className={
        'inline-flex items-center justify-center rounded-full ' +
        'bg-gradient-to-r from-accent-teal via-accent-cobalt to-accent-violet ' +
        'px-6 py-3 text-base font-semibold text-white ' +
        'shadow-[0_10px_30px_-10px_rgba(37,99,235,0.5)] transition-all ' +
        'hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-12px_rgba(124,58,237,0.7)] ' +
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 ' +
        className
      }
    >
      {children}
    </button>
  );
}
