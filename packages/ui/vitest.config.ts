/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    exclude: ['node_modules', 'dist', '.turbo'],
    // Configure jsdom environment options
    environmentOptions: {
      jsdom: {
        url: 'http://localhost:3000',
        // Explicitly enable localStorage for jsdom
        storageQuota: 10000000,
      },
    },
    // Code coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'dist/',
        '.turbo/',
        'src/test-setup.ts',
        '**/*.spec.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
        '**/*.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
        'e2e/',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
