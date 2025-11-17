import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock window.location for tests
Object.defineProperty(window, 'location', {
  value: {
    origin: 'http://localhost:3000',
    href: 'http://localhost:3000',
    pathname: '/',
    search: '',
    hash: '',
  },
  writable: true,
});

// Polyfill localStorage.clear() for jsdom environment
if (typeof window !== 'undefined' && window.localStorage && !window.localStorage.clear) {
  window.localStorage.clear = function () {
    const keys: string[] = [];
    for (let i = 0; i < this.length; i++) {
      const key = this.key(i);
      if (key !== null) {
        keys.push(key);
      }
    }
    keys.forEach((key) => this.removeItem(key));
  };
}

// Mock console methods to reduce noise in tests
globalThis.console = {
  ...console,
  // Uncomment the next line if you want to silence console.log during tests
  // log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};
