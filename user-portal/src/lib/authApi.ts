import { apiFetch, ApiError } from './api';

export interface SessionBundle {
  idToken: string;
  refreshToken: string;
  expiresIn: number;
}

export interface SignupInput {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
  remember: boolean;
}

export interface VerifyInput {
  email: string;
  code: string;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let code = 'UNKNOWN';
    let message = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      if (errBody.error) {
        code = errBody.error.code ?? code;
        message = errBody.error.message ?? message;
      }
    } catch {
      // ignore
    }
    throw new ApiError(response.status, code, message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function signupRequest(input: SignupInput): Promise<{ userId: string }> {
  const body = await post<{ data: { userId: string } }>(
    '/api/v1/auth/signup',
    input,
  );
  return body.data;
}

export async function loginRequest(input: LoginInput): Promise<SessionBundle> {
  const body = await post<{ data: SessionBundle }>('/api/v1/auth/login', input);
  return body.data;
}

export async function verifyEmailRequest(input: VerifyInput): Promise<SessionBundle> {
  const body = await post<{ data: SessionBundle }>(
    '/api/v1/auth/verify-email',
    input,
  );
  return body.data;
}

export async function resendCodeRequest(email: string): Promise<void> {
  await post<void>('/api/v1/auth/resend-code', { email });
}

export async function forgotPasswordRequest(email: string): Promise<void> {
  await post<void>('/api/v1/auth/forgot', { email });
}

export async function resetPasswordRequest(input: {
  token: string;
  password: string;
}): Promise<SessionBundle> {
  const body = await post<{ data: SessionBundle }>('/api/v1/auth/reset', input);
  return body.data;
}
