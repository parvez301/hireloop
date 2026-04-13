/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_COGNITO_USER_POOL_ID?: string;
  readonly VITE_COGNITO_CLIENT_ID?: string;
  readonly VITE_COGNITO_REGION?: string;
  readonly VITE_ENVIRONMENT?: string;
  readonly VITE_SSE_KEEPALIVE_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
