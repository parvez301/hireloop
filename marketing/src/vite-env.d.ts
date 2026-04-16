/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USER_PORTAL_URL?: string;
  readonly VITE_ENVIRONMENT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module '*.md?raw' {
  const content: string;
  export default content;
}
