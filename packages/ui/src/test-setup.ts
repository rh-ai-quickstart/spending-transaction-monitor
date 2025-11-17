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

/**
 * localStorage polyfill for jsdom v26+
 *
 * jsdom 26.x has a broken localStorage implementation that doesn't provide
 * the standard Storage API methods. This polyfill provides a complete
 * localStorage implementation for tests.
 *
 * IMPORTANT: This implementation makes storage keys enumerable via Object.keys()
 * to match real browser behavior and support code that iterates localStorage keys.
 */
if (
  typeof window !== 'undefined' &&
  (!window.localStorage || typeof window.localStorage.setItem !== 'function')
) {
  class LocalStorageMock implements Storage {
    // Index signature for stored values - allows dynamic property access
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;

    getItem(key: string): string | null {
      return this[key] ?? null;
    }

    setItem(key: string, value: string): void {
      this[key] = String(value);
    }

    removeItem(key: string): void {
      delete this[key];
    }

    clear(): void {
      // Get all keys except the Storage API methods
      const keys = Object.keys(this);
      keys.forEach((key) => {
        if (
          key !== 'getItem' &&
          key !== 'setItem' &&
          key !== 'removeItem' &&
          key !== 'clear' &&
          key !== 'key' &&
          key !== 'length'
        ) {
          delete this[key];
        }
      });
    }

    key(index: number): string | null {
      const keys = Object.keys(this).filter(
        (k) =>
          k !== 'getItem' &&
          k !== 'setItem' &&
          k !== 'removeItem' &&
          k !== 'clear' &&
          k !== 'key' &&
          k !== 'length',
      );
      return keys[index] ?? null;
    }

    get length(): number {
      return Object.keys(this).filter(
        (k) =>
          k !== 'getItem' &&
          k !== 'setItem' &&
          k !== 'removeItem' &&
          k !== 'clear' &&
          k !== 'key' &&
          k !== 'length',
      ).length;
    }
  }

  const localStorageMock = new LocalStorageMock();

  // Replace localStorage with working implementation
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });

  // Also set on globalThis for tests that access it directly
  Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });
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
