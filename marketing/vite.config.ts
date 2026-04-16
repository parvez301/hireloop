import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function runLlmsGenerator(): void {
  execFileSync(process.execPath, [
    path.join(__dirname, 'node_modules', 'tsx', 'dist', 'cli.mjs'),
    path.join(__dirname, 'scripts', 'generate-llms-txt.ts'),
  ], { cwd: __dirname, stdio: 'inherit' });
}

function llmsGeneratorPlugin() {
  return {
    name: 'generate-llms-txt',
    buildStart() {
      runLlmsGenerator();
    },
  };
}

export default defineConfig({
  plugins: [react(), llmsGeneratorPlugin()],
  server: {
    port: 5175,
    strictPort: true,
  },
});
