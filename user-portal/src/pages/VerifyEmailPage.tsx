import { useEffect, useState } from 'react';

import {
  AuthError,
  AuthField,
  AuthShell,
  GradientSubmit,
} from '../components/auth/AuthShell';
import { ApiError } from '../lib/api';
import { storeSession } from '../lib/auth';
import { resendCodeRequest, verifyEmailRequest } from '../lib/authApi';

type Props = { email: string };

const RESEND_COOLDOWN_S = 30;

export default function VerifyEmailPage({ email }: Props) {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [cooldownS, setCooldownS] = useState(RESEND_COOLDOWN_S);

  useEffect(() => {
    if (cooldownS <= 0) return;
    const id = setTimeout(() => setCooldownS((previous) => previous - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldownS]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session = await verifyEmailRequest({ email, code });
      storeSession(session);
      window.location.assign('/');
    } catch (caught) {
      const message =
        caught instanceof ApiError ? caught.message : (caught as Error).message;
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  async function onResend() {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await resendCodeRequest(email);
      setInfo(`We sent a new code to ${email}.`);
      setCooldownS(RESEND_COOLDOWN_S);
    } catch (caught) {
      const message =
        caught instanceof ApiError ? caught.message : (caught as Error).message;
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={
        <>
          Check your{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            inbox
          </span>
        </>
      }
      subtitle={`We sent a 6-digit code to ${email || 'your email'}. Enter it below to finish setting up your account.`}
      footer={
        <span>
          Wrong email?{' '}
          <a href="/signup" className="text-accent-cobalt hover:underline">
            Start over
          </a>
        </span>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <AuthField
          label="6-digit code"
          inputMode="numeric"
          autoComplete="one-time-code"
          required
          pattern="\d{6}"
          maxLength={6}
          value={code}
          onChange={(event) =>
            setCode(event.target.value.replace(/\D/g, '').slice(0, 6))
          }
          disabled={busy}
          placeholder="123456"
        />
        <GradientSubmit disabled={busy || code.length !== 6}>
          {busy ? 'Verifying…' : 'Verify and continue'}
        </GradientSubmit>
        <div className="flex items-center justify-between text-[12px] text-ink-3">
          <button
            type="button"
            onClick={() => void onResend()}
            disabled={busy || cooldownS > 0}
            className="underline decoration-dotted underline-offset-4 hover:text-ink-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {cooldownS > 0
              ? `Resend code in ${cooldownS}s`
              : 'Resend code'}
          </button>
          <a
            href="/signup"
            className="underline decoration-dotted underline-offset-4 hover:text-ink-2"
          >
            Use a different email
          </a>
        </div>
        {info && (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[13px] text-emerald-800">
            {info}
          </p>
        )}
        <AuthError>{error}</AuthError>
      </form>
    </AuthShell>
  );
}
