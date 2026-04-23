import type { ReactNode } from 'react';

import { AuthBrandPanel } from './AuthBrandPanel';

type Props = {
  eyebrow?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  brandPanel?: boolean;
  headerSwap?: ReactNode;
};

export function AuthShell({
  eyebrow,
  title,
  subtitle,
  footer,
  children,
  brandPanel = true,
  headerSwap,
}: Props) {
  return (
    <main className="grid min-h-screen grid-cols-1 bg-bg text-ink lg:grid-cols-2 [font-feature-settings:'ss01','cv11']">
      <section className="relative flex flex-col px-6 py-8 lg:px-16 lg:py-10">
        <header className="flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="h-7 w-7 rounded-md"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            />
            <span className="text-[15px] font-semibold tracking-tight text-ink">
              HireLoop
            </span>
          </a>
          {headerSwap && (
            <div className="text-[12px] text-ink-3">{headerSwap}</div>
          )}
        </header>

        <div className="mx-auto my-auto w-full max-w-md py-10 animate-fade-up motion-reduce:animate-none">
          {eyebrow && (
            <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              {eyebrow}
            </p>
          )}
          <h1 className="mt-3 text-[40px] font-semibold leading-[1.05] tracking-[-0.02em] text-ink">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-3 text-[14px] leading-relaxed text-ink-3">
              {subtitle}
            </p>
          )}

          <div className="mt-8">{children}</div>

          {footer && <div className="mt-6 text-[13px] text-ink-3">{footer}</div>}
        </div>

        <footer className="mt-auto flex items-center justify-between text-[11px] text-ink-4">
          <span>© HireLoop</span>
          <div className="flex gap-4">
            <a className="hover:text-ink-3" href="/privacy">
              Privacy
            </a>
            <a className="hover:text-ink-3" href="/terms">
              Terms
            </a>
            <a className="hover:text-ink-3" href="mailto:support@hireloop.xyz">
              Support
            </a>
          </div>
        </footer>
      </section>

      {brandPanel && <AuthBrandPanel />}
    </main>
  );
}

type FieldProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

export function AuthField({ label, className = '', ...rest }: FieldProps) {
  return (
    <label className="block">
      <span className="block text-[12px] font-medium text-ink-2">{label}</span>
      <input
        {...rest}
        className={
          'mt-1.5 block w-full rounded-xl border border-line-2 bg-white px-3.5 py-3 text-[14px] text-ink ' +
          'placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5 ' +
          'disabled:cursor-not-allowed disabled:opacity-60 ' +
          className
        }
      />
    </label>
  );
}

export function GradientSubmit({
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="submit"
      {...rest}
      style={{
        backgroundImage:
          'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
        ...(rest.style ?? {}),
      }}
      className={
        'flex w-full items-center justify-center rounded-xl px-4 py-3 text-[14px] font-semibold text-white ' +
        'shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),0_2px_6px_-2px_rgba(15,23,42,0.12),inset_0_1px_0_rgba(255,255,255,0.15)] ' +
        'transition-all duration-150 hover:-translate-y-px ' +
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 ' +
        'motion-reduce:transition-none motion-reduce:hover:translate-y-0 ' +
        (rest.className ?? '')
      }
    >
      {children}
    </button>
  );
}

export function AuthError({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p
      role="alert"
      className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
    >
      {children}
    </p>
  );
}
