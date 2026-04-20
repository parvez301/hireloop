const TOKEN_KEY = 'ca:idToken';
const REFRESH_KEY = 'ca:refreshToken';
const EXPIRES_AT_KEY = 'ca:expiresAt';

function cognitoDomain(): string {
  const explicit = import.meta.env.VITE_COGNITO_DOMAIN?.replace(/\/$/, '').trim();
  if (explicit) return explicit;
  const env = import.meta.env.VITE_ENVIRONMENT ?? 'dev';
  const region = import.meta.env.VITE_COGNITO_REGION ?? 'us-east-1';
  return `hireloop-${env}.auth.${region}.amazoncognito.com`;
}

function redirectUri(): string {
  const explicit = import.meta.env.VITE_AUTH_REDIRECT_URI?.trim();
  if (explicit) return explicit;
  return `${window.location.origin}/auth/callback`;
}

function clientId(): string {
  const cid = import.meta.env.VITE_COGNITO_CLIENT_ID?.trim();
  if (!cid) throw new Error('VITE_COGNITO_CLIENT_ID not configured');
  return cid;
}

export function hostedUiUrl(variant: 'signup' | 'login'): string {
  const params = new URLSearchParams({
    client_id: clientId(),
    response_type: 'code',
    scope: 'openid email profile',
    redirect_uri: redirectUri(),
  });
  return `https://${cognitoDomain()}/${variant}?${params.toString()}`;
}

export function logoutUrl(): string {
  const params = new URLSearchParams({
    client_id: clientId(),
    logout_uri: `${window.location.origin}/`,
  });
  return `https://${cognitoDomain()}/logout?${params.toString()}`;
}

export type TokenBundle = {
  idToken: string;
  refreshToken: string | null;
  expiresAt: number;
};

export async function exchangeCodeForTokens(code: string): Promise<TokenBundle> {
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: clientId(),
    code,
    redirect_uri: redirectUri(),
  });
  const response = await fetch(`https://${cognitoDomain()}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`Token exchange failed: ${response.status} ${text}`);
  }
  const json = (await response.json()) as {
    id_token: string;
    refresh_token?: string;
    expires_in: number;
  };
  return {
    idToken: json.id_token,
    refreshToken: json.refresh_token ?? null,
    expiresAt: Date.now() + json.expires_in * 1000,
  };
}

export function storeTokens(bundle: TokenBundle): void {
  localStorage.setItem(TOKEN_KEY, bundle.idToken);
  if (bundle.refreshToken) {
    localStorage.setItem(REFRESH_KEY, bundle.refreshToken);
  }
  localStorage.setItem(EXPIRES_AT_KEY, String(bundle.expiresAt));
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
