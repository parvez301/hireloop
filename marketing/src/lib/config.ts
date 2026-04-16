export const USER_PORTAL_URL = (
  import.meta.env.VITE_USER_PORTAL_URL ?? 'http://localhost:5173'
).replace(/\/$/, '');

export function signupUrl(): string {
  return `${USER_PORTAL_URL}/signup`;
}
