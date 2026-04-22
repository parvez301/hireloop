import { useEffect } from 'react';

import { isAuthenticated } from '../lib/auth';

/**
 * Legacy Cognito OAuth callback — unreachable in the in-house auth flow but
 * kept so bookmarked links don't 404. Redirects authenticated users to /,
 * everyone else to /login.
 */
export default function AuthCallbackPage() {
  useEffect(() => {
    window.location.replace(isAuthenticated() ? '/' : '/login');
  }, []);
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-6">
      <div className="text-center">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-blue-600" />
        <h1 className="mt-6 text-xl font-semibold text-gray-900">
          Signing you in…
        </h1>
      </div>
    </div>
  );
}
