import { useState } from 'react';

import {
  AuthError,
  AuthField,
  AuthShell,
  GradientSubmit,
} from '../components/auth/AuthShell';
import { ApiError } from '../lib/api';
import { storeSession } from '../lib/auth';
import { loginRequest } from '../lib/authApi';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session = await loginRequest({ email, password, remember });
      storeSession(session);
      window.location.assign('/');
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === 'EMAIL_UNVERIFIED') {
        try {
          sessionStorage.setItem('auth:pendingVerifyEmail', email);
        } catch {
          // ignore — verify page will prompt for email if needed
        }
        window.location.assign('/auth/verify');
        return;
      }
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
          Sign in to{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            HireLoop
          </span>
        </>
      }
      subtitle="Pick up where you left off. Your evaluations, pipeline, and scans are waiting."
      footer={
        <div className="flex items-center justify-between">
          <span>
            Don't have an account?{' '}
            <a href="/signup" className="text-accent-cobalt hover:underline">
              Sign up
            </a>
          </span>
          <a
            href="/auth/forgot"
            className="text-ink-4 underline decoration-dotted underline-offset-4 hover:text-ink-2"
          >
            Forgot password?
          </a>
        </div>
      }
    >
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
        <AuthField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={busy}
        />
        <label className="flex items-center gap-2 text-[12px] text-ink-3">
          <input
            type="checkbox"
            checked={remember}
            onChange={(event) => setRemember(event.target.checked)}
          />
          Keep me signed in
        </label>
        <GradientSubmit disabled={busy || !email || !password}>
          {busy ? 'Signing in…' : 'Sign in'}
        </GradientSubmit>
        <AuthError>{error}</AuthError>
      </form>
    </AuthShell>
  );
}
