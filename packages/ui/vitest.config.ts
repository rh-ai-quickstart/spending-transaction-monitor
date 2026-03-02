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
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.{test,spec}.{ts,tsx}',
        'src/test-setup.ts',
        'src/**/*.stories.tsx',
        'src/main.tsx',
        // Exclude UI wrapper components (Radix UI wrappers and presentational components)
        'src/components/atoms/**',
        'src/components/theme-provider/**',
        'src/components/mode-toggle/**',
        'src/components/footer/**',
        'src/components/dev-mode/**',
        'src/components/user-avatar/**',
        'src/components/dashboard-header/**',
        'src/components/stat-card/**',
        'src/components/stats-list/**',
        'src/components/transaction-card/**',
        'src/components/transaction-drawer/**',
        'src/components/transaction-sidebar/**',
        'src/components/alerts-panel/**',
        'src/components/alert-recommendations/**',
        'src/components/alert-rule-card/**',
        'src/components/alert-rule-form/**',
        'src/components/alert-rule-validation/**',
        'src/components/alert-history-popover/**',
        'src/components/transaction-list/**',
        'src/components/transaction-chart/**',
        'src/components/add-transaction-form/**',
        // Exclude route/page components (complex UI components)
        'src/routes/**',
        // Exclude schemas (Zod definitions, no logic to test)
        'src/schemas/**',
        // Exclude complex infrastructure (WebSocket, geolocation wrappers, location services)
        'src/hooks/useWebSocket.ts',
        'src/hooks/useLocation.ts',
        'src/hooks/recommendations.ts',
        'src/services/geolocation.ts',
        'src/services/api-recommendations.ts',
        'src/services/alert.ts',
        'src/config/**',
        'src/components/location/**',
        'src/components/auth/AuthErrorBoundary.tsx',
        // Exclude generated/type files
        'src/routeTree.gen.ts',
        'src/types/**',
        'src/**/*.d.ts',
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
