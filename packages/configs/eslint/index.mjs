import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import prettier from 'eslint-config-prettier';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx,js,jsx}'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true }
      },
      globals: {
        // Browser globals
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        requestAnimationFrame: 'readonly',
        getComputedStyle: 'readonly',
        navigator: 'readonly',
        innerWidth: 'readonly',
        innerHeight: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLTextAreaElement: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLButtonElement: 'readonly',
        HTMLFormElement: 'readonly',
        HTMLParagraphElement: 'readonly',
        HTMLSpanElement: 'readonly',
        ResizeObserver: 'readonly',
        localStorage: 'readonly',
        fetch: 'readonly',
        alert: 'readonly',
        // Storybook globals
        __STORYBOOK_CLIENT_LOGGER__: 'readonly',
      }
    },
    plugins: {
      '@typescript-eslint': tseslint,
      'react': react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh
    },
    settings: {
      react: { version: 'detect' }
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { 
        allowConstantExport: true,
        allowExportNames: ['badgeVariants', 'buttonVariants', 'useTheme']
      }],
      // React 19 has automatic JSX runtime, no need to import React
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',
      // Allow unescaped entities in JSX (quotes, apostrophes are fine)
      'react/no-unescaped-entities': 'off',
      // Disable prop-types validation since we use TypeScript
      'react/prop-types': 'off',
    }
  },
  // Node.js config for build tools
  {
    files: ['**/*.config.{ts,js,mjs}', '**/vite.config.*'],
    languageOptions: {
      parser: tsparser,
      globals: {
        __dirname: 'readonly',
        __filename: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        global: 'readonly',
        React: 'readonly',
      }
    }
  },
  // Ignore generated files
  {
    ignores: ['storybook-static/**', 'dist/**', 'build/**']
  },
  prettier
];


