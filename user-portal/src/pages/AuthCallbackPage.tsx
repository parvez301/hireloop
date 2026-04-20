import { useEffect, useState } from 'react';

import { exchangeCodeForTokens, storeTokens } from '../lib/auth';

type Status = 'exchanging' | 'error';

export default function AuthCallbackPage() {
  const [status, setStatus] = useState<Status>('exchanging');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const cognitoError = params.get('error_description') ?? params.get('error');

    if (cognitoError) {
      setStatus('error');
      setErrorMessage(cognitoError);
      return;
    }
    if (!code) {
      setStatus('error');
      setErrorMessage('Missing authorization code. Try signing up again.');
      return;
    }

    exchangeCodeForTokens(code)
      .then((bundle) => {
        storeTokens(bundle);
        window.location.replace('/');
      })
      .catch((err: Error) => {
        setStatus('error');
        setErrorMessage(err.message || 'Could not complete sign-in.');
      });
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-6">
      <div className="w-full max-w-md text-center">
        {status === 'exchanging' && (
          <>
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-blue-600" />
            <h1 className="mt-6 text-xl font-semibold text-gray-900">Signing you in…</h1>
            <p className="mt-2 text-sm text-gray-600">One moment while we finish the handshake.</p>
          </>
        )}
        {status === 'error' && (
          <>
            <h1 className="text-xl font-semibold text-gray-900">Sign-in didn&apos;t complete</h1>
            <p className="mt-2 text-sm text-gray-600">{errorMessage}</p>
            <a
              href="/signup"
              className="mt-6 inline-flex items-center justify-center rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
              Try again
            </a>
          </>
        )}
      </div>
    </div>
  );
}
