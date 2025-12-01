/**
 * Runtime environment configuration
 * These values are injected at container startup via env-config.js
 */
import type { RuntimeEnv } from '../schemas/config';

declare global {
  interface Window {
    ENV?: RuntimeEnv;
  }
}

export {};
