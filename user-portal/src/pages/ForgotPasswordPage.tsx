import { useState } from 'react';

import {
  AuthError,
  AuthField,
  AuthShell,
  GradientSubmit,
} from '../components/auth/AuthShell';
import { ApiError } from '../lib/api';
import { forgotPasswordRequest } from '../lib/authApi';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await forgotPasswordRequest(email);
      setDone(true);
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
          Forgot your{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            password
          </span>
          ?
        </>
      }
      subtitle="Enter the email on your account. We'll send you a link to reset it."
      footer={
        <span>
          Remembered it?{' '}
          <a href="/login" className="text-accent-cobalt hover:underline">
            Back to sign in
          </a>
        </span>
      }
    >
      {done ? (
        <div className="rounded-2xl border border-line bg-white p-5 text-[14px] text-ink-2">
          <p className="font-medium text-ink">Check your inbox.</p>
          <p className="mt-1 text-[13px] text-ink-3">
            If an account exists for <span className="text-ink-2">{email}</span>,
            we've sent a reset link. The link is good for 30 minutes.
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <AuthField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={busy}
          />
          <GradientSubmit disabled={busy || !email}>
            {busy ? 'Sending…' : 'Send reset link'}
          </GradientSubmit>
          <AuthError>{error}</AuthError>
        </form>
      )}
    </AuthShell>
  );
}
