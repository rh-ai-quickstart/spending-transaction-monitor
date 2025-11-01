/**
 * Authentication configuration
 * Handles both development bypass and production OIDC setup
 */

export interface AuthConfig {
  bypassAuth: boolean;
  environment: 'development' | 'production' | 'staging' | 'test';
  keycloak: {
    authority: string;
    clientId: string;
    redirectUri: string;
    postLogoutRedirectUri: string;
  };
}

// Helper to get config values with proper fallbacks
// This function is called lazily to ensure window.ENV is loaded
function getAuthConfig(): AuthConfig {
  // Environment detection - check both build-time and runtime configuration
  const environment = (import.meta.env.VITE_ENVIRONMENT ||
    (typeof window !== 'undefined' && window.ENV?.ENVIRONMENT) ||
    'development') as AuthConfig['environment'];

  // Bypass detection - check both build-time and runtime configuration
  // This ensures frontend and backend auth bypass are always in sync
  const bypassAuth =
    import.meta.env.VITE_BYPASS_AUTH === 'true' ||
    (typeof window !== 'undefined' && window.ENV?.BYPASS_AUTH === true);

  const authority =
    import.meta.env.VITE_KEYCLOAK_URL ||
    (typeof window !== 'undefined' && window.ENV?.KEYCLOAK_URL) ||
    'http://localhost:8080/realms/spending-monitor';

  const clientId =
    import.meta.env.VITE_KEYCLOAK_CLIENT_ID ||
    (typeof window !== 'undefined' && window.ENV?.KEYCLOAK_CLIENT_ID) ||
    'spending-monitor';

  const redirectUri =
    import.meta.env.VITE_KEYCLOAK_REDIRECT_URI ||
    (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');

  const postLogoutRedirectUri =
    import.meta.env.VITE_KEYCLOAK_POST_LOGOUT_REDIRECT_URI ||
    (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');

  // Debug logging in production to help diagnose config issues
  if (typeof window !== 'undefined' && window.ENV?.DEV) {
    console.log('🔧 Auth config loaded:', {
      environment,
      bypassAuth,
      authority,
      clientId,
      'window.ENV.KEYCLOAK_URL': window.ENV?.KEYCLOAK_URL,
    });
  }

  return {
    environment,
    bypassAuth,
    keycloak: {
      authority,
      clientId,
      redirectUri,
      postLogoutRedirectUri,
    },
  };
}

// Create a proxy to ensure lazy evaluation
export const authConfig: AuthConfig = new Proxy({} as AuthConfig, {
  get(_, prop) {
    const config = getAuthConfig();
    return (config as never)[prop];
  },
});

// Auth configuration loaded
