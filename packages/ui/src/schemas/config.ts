import { z } from 'zod';

/**
 * Runtime Environment Configuration Schema
 * These values are injected at container startup via env-config.js
 */
export const RuntimeEnvSchema = z.object({
  BYPASS_AUTH: z.boolean(),
  API_BASE_URL: z.string(),
  ENVIRONMENT: z.enum(['development', 'staging', 'production']),
  KEYCLOAK_URL: z.string(),
  KEYCLOAK_REALM: z.string(),
  KEYCLOAK_CLIENT_ID: z.string(),
});

// Export type
export type RuntimeEnv = z.infer<typeof RuntimeEnvSchema>;
