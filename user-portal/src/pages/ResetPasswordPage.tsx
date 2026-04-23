import { useState } from 'react';

import {
  AuthError,
  AuthShell,
  GradientSubmit,
} from '../components/auth/AuthShell';
import { PasswordField } from '../components/auth/PasswordField';
import { ApiError } from '../lib/api';
import { storeSession } from '../lib/auth';
import { resetPasswordRequest } from '../lib/authApi';

type Props = { token: string };

export default function ResetPasswordPage({ token }: Props) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasToken = token.length > 0;
  const mismatch = confirm.length > 0 && password !== confirm;

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasToken) return;
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const session = await resetPasswordRequest({ token, password });
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

  return (
    <AuthShell
      title={
        <>
          Pick something{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            memorable
          </span>
        </>
      }
      subtitle="We'll sign you in as soon as you save it."
      footer={
        <span>
          <a href="/login" className="text-accent-cobalt hover:underline">
            Back to sign in
          </a>
        </span>
      }
    >
      {!hasToken ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-[14px] text-red-800">
          <p className="font-medium">This reset link is missing its token.</p>
          <p className="mt-1 text-[13px]">
            Start a new password reset from the{' '}
            <a href="/auth/forgot" className="underline">
              forgot password page
            </a>
            .
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <PasswordField
            label="New password"
            autoComplete="new-password"
            required
            minLength={10}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
            strength
          />
          <PasswordField
            label="Confirm new password"
            autoComplete="new-password"
            required
            minLength={10}
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            disabled={busy}
          />
          {mismatch && (
            <p className="text-[12px] text-amber">Passwords don't match.</p>
          )}
          <GradientSubmit
            disabled={
              busy ||
              password.length < 10 ||
              confirm.length < 10 ||
              password !== confirm
            }
          >
            {busy ? 'Saving…' : 'Save and sign in'}
          </GradientSubmit>
          <AuthError>{error}</AuthError>
        </form>
      )}
    </AuthShell>
  );
}
