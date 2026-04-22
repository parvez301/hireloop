const TOKEN_KEY = 'ca:idToken';
const REFRESH_KEY = 'ca:refreshToken';
const EXPIRES_AT_KEY = 'ca:expiresAt';

/**
 * In-house auth replaced Cognito Hosted UI. `hostedUiUrl` is preserved as a
 * symbol so existing `window.location.replace(hostedUiUrl(...))` callers
 * still compile, but it now returns our local route. The Cognito domain /
 * OAuth code exchange helpers have been removed.
 */
export function hostedUiUrl(variant: 'signup' | 'login'): string {
  return `/${variant}`;
}

export type TokenBundle = {
  idToken: string;
  refreshToken: string | null;
  expiresAt: number;
};

export function storeTokens(bundle: TokenBundle): void {
  localStorage.setItem(TOKEN_KEY, bundle.idToken);
  if (bundle.refreshToken) {
    localStorage.setItem(REFRESH_KEY, bundle.refreshToken);
  }
  localStorage.setItem(EXPIRES_AT_KEY, String(bundle.expiresAt));
}

export function storeSession(session: {
  idToken: string;
  refreshToken: string;
  expiresIn: number;
}): void {
  storeTokens({
    idToken: session.idToken,
    refreshToken: session.refreshToken,
    expiresAt: Date.now() + session.expiresIn * 1000,
  });
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
}

export function isAuthenticated(): boolean {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return false;
  const expiresAt = Number(localStorage.getItem(EXPIRES_AT_KEY));
  return !expiresAt || expiresAt > Date.now();
}

function base64UrlDecode(segment: string): string {
  const padLen = (4 - (segment.length % 4)) % 4;
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(padLen);
  return atob(base64);
}

export function getIdTokenClaims(): Record<string, unknown> | null {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    return JSON.parse(base64UrlDecode(parts[1])) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getUserEmail(): string | null {
  const claims = getIdTokenClaims();
  const email = claims?.email;
  return typeof email === 'string' ? email : null;
}

export function logout(): void {
  clearTokens();
  window.location.assign('/login');
}
