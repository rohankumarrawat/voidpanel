import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(__dirname, '..');
  const env = loadEnv(mode, rootDir, '');
  const port = env.PORT || process.env.PORT || 5000;

  return {
    plugins: [react()],
    build: {
      outDir: '../public',
      emptyOutDir: true,
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: `http://127.0.0.1:${port}`,
          changeOrigin: true,
        },
      },
    },
  };
});

