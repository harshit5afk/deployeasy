import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/demo': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/sandbox': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/test-mode': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/health': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/version': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/metrics': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      // FastAPI's documentation pages fetch /openapi.json from the same
      // origin, so proxy both the pages and schema during local development.
      '/docs': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/redoc': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/openapi.json': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: '../app/static/dist',
    emptyOutDir: true
  }
});
