import { useState } from 'react';

import {
  AuthError,
  AuthField,
  AuthShell,
  GradientSubmit,
} from '../components/auth/AuthShell';
import { PasswordField } from '../components/auth/PasswordField';
import { ApiError } from '../lib/api';
import { signupRequest } from '../lib/authApi';

export default function SignupPage() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signupRequest({ firstName, lastName, email, password });
      try {
        sessionStorage.setItem('auth:pendingVerifyEmail', email);
      } catch {
        // sessionStorage may fail in private-mode
      }
      window.location.assign('/auth/verify');
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
      eyebrow="Start for free"
      title={
        <>
          Create your{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            HireLoop
          </span>{' '}
          account
        </>
      }
      subtitle="Takes 20 seconds. No credit card. Your first evaluation is on us."
      headerSwap={
        <span>
          Already a member?{' '}
          <a href="/login" className="font-medium text-ink hover:underline">
            Sign in
          </a>
        </span>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <AuthField
            label="First name"
            autoComplete="given-name"
            required
            placeholder="Ava"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            disabled={busy}
          />
          <AuthField
            label="Last name"
            autoComplete="family-name"
            required
            placeholder="Chen"
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            disabled={busy}
          />
        </div>
        <AuthField
          label="Email"
          type="email"
          autoComplete="email"
          required
          placeholder="ava@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={busy}
        />
        <PasswordField
          autoComplete="new-password"
          required
          minLength={10}
          placeholder="At least 10 characters"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={busy}
          strength
        />
        <GradientSubmit
          disabled={busy || !firstName || !lastName || !email || password.length < 10}
        >
          {busy ? 'Creating account…' : 'Create account'}
        </GradientSubmit>
        <AuthError>{error}</AuthError>
        <p className="mt-2 text-center text-[12px] text-ink-3">
          By creating an account you agree to our{' '}
          <a href="#" className="text-ink hover:underline">
            Terms
          </a>{' '}
          and{' '}
          <a href="#" className="text-ink hover:underline">
            Privacy Policy
          </a>
          .
        </p>
      </form>
    </AuthShell>
  );
}
