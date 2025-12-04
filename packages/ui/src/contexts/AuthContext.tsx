/**
 * Authentication Context
 * Provides auth functionality with development bypass support
 */
/* eslint-disable react-refresh/only-export-components */

import React, { createContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  AuthProvider as OIDCProvider,
  useAuth as useOIDCAuth,
} from 'react-oidc-context';
import { authConfig } from '../config/auth';
import type { User, AuthContextType } from '../schemas/auth';
import { DEV_USER } from '../constants/auth';
import { ApiClient } from '../services/apiClient';
import { clearStoredLocation } from '../hooks/useLocation';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Check if stored OIDC data matches current configuration
 * Returns true if there's a mismatch (stale data from different deployment)
 */
function hasStaleAuthData(): boolean {
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('oidc.user:')) {
        // Extract the authority from the key (format: oidc.user:{authority}:{clientId})
        const parts = key.split(':');
        if (parts.length >= 2) {
          const storedAuthority = parts.slice(1, -1).join(':'); // Handle : in authority URL
          const currentAuthority = authConfig.keycloak.authority;

          if (storedAuthority !== currentAuthority) {
            if (import.meta.env.DEV) {
              console.log('🔍 Detected stale auth data:', {
                stored: storedAuthority,
                current: currentAuthority,
              });
            }
            return true;
          }
        }
      }
    }
  } catch (err) {
    console.error('Error checking for stale auth data:', err);
  }
  return false;
}

/**
 * Clear all authentication-related storage (localStorage and cookies)
 * This is useful when authentication fails due to stale tokens/cookies
 */
function clearAuthStorage(): void {
  if (import.meta.env.DEV) {
    console.log('🧹 Clearing all auth storage...');
  }

  // Clear OIDC-related items from localStorage
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && (key.includes('oidc') || key.includes('keycloak'))) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((key) => {
    localStorage.removeItem(key);
    if (import.meta.env.DEV) {
      console.log(`  Removed localStorage: ${key}`);
    }
  });

  // Clear cookies related to auth
  const cookies = document.cookie.split(';');
  cookies.forEach((cookie) => {
    const cookieName = cookie.split('=')[0].trim();
    if (
      cookieName.includes('oidc') ||
      cookieName.includes('keycloak') ||
      cookieName.includes('AUTH') ||
      cookieName.includes('session')
    ) {
      // Clear cookie by setting expiry to past date
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      if (import.meta.env.DEV) {
        console.log(`  Removed cookie: ${cookieName}`);
      }
    }
  });

  // Clear token from ApiClient
  ApiClient.setToken(null);

  // Clear location data
  clearStoredLocation();

  if (import.meta.env.DEV) {
    console.log('✅ Auth storage cleared');
  }
}

/**
 * Development Auth Provider - bypasses OIDC
 */
const DevAuthProvider = React.memo(({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const login = useCallback(() => {
    // No-op in dev mode since user is always authenticated
  }, []);

  const logout = useCallback(() => {
    if (import.meta.env.DEV) {
      console.log('🔓 Dev mode: logout() called - staying authenticated');
    }
    clearStoredLocation(); // Clear location data on logout (frontend cleanup)
    // Note: Location clearing also handled by backend on logout
    // No-op in dev mode since user stays authenticated
  }, []);

  const signinRedirect = useCallback(() => {
    // No-op in dev mode since user is already authenticated
  }, []);

  // Fetch user from backend on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Create apiClient instance for this request
        const client = new ApiClient();
        const response = await client.fetch('/api/users/profile');
        if (response.ok) {
          const apiUser = await response.json();
          const devUser: User = {
            id: apiUser.id,
            email: apiUser.email,
            username: apiUser.email.split('@')[0],
            name: `${apiUser.first_name} ${apiUser.last_name}`,
            roles: ['user', 'admin'], // Dev mode gets all roles
            isDevMode: true,
          };
          setUser(devUser);

          if (import.meta.env.DEV) {
            console.log('🔓 Dev mode: Loaded user from API:', {
              id: devUser.id,
              email: devUser.email,
            });
          }
        } else {
          // Fallback to hardcoded DEV_USER if API fails
          console.warn('Failed to fetch user from API, using fallback DEV_USER');
          setUser(DEV_USER);
        }
      } catch (err) {
        console.error('Error fetching dev user:', err);
        setError(new Error('Failed to load user'));
        // Fallback to hardcoded DEV_USER
        setUser(DEV_USER);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, []);

  const contextValue: AuthContextType = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      signinRedirect,
      error,
    }),
    [user, isLoading, login, logout, signinRedirect, error],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
});
DevAuthProvider.displayName = 'DevAuthProvider';

/**
 * Production OIDC Auth Provider
 */
const ProductionAuthProvider = React.memo(
  ({ children }: { children: React.ReactNode }) => {
    // Check for and clear stale auth data BEFORE OIDC provider initializes
    // This must run synchronously on first render
    const [isReady, setIsReady] = useState(() => {
      if (hasStaleAuthData()) {
        if (import.meta.env.DEV) {
          console.log('🧹 Clearing stale auth data from previous deployment...');
        }
        clearAuthStorage();
        return true; // Ready after clearing
      }
      return true;
    });

    const oidcConfig = useMemo(
      () => ({
        authority: authConfig.keycloak.authority,
        client_id: authConfig.keycloak.clientId,
        redirect_uri: authConfig.keycloak.redirectUri,
        post_logout_redirect_uri: authConfig.keycloak.postLogoutRedirectUri,
        response_type: 'code',
        scope: 'openid profile email',
        automaticSilentRenew: true, // Automatically refresh tokens before expiry
        // Ensure localStorage persistence
        storeUser: true, // Explicitly enable user storage
        userStore: undefined, // Use default WebStorageStateStore (localStorage)
        // Remove problematic config
        loadUserInfo: false,
        monitorSession: false,
        // Token refresh settings
        accessTokenExpiringNotificationTimeInSeconds: 60, // Notify 60 seconds before expiry
        // Handle silent renew errors gracefully
        onSigninCallback: () => {
          // Clear the URL after successful signin
          window.history.replaceState({}, document.title, window.location.pathname);
        },
      }),
      [],
    );

    useEffect(() => {
      // OIDC config initialized
      setIsReady(true);
    }, [oidcConfig]);

    if (!isReady) {
      return null; // Don't render until stale data is cleared
    }

    return (
      <OIDCProvider {...oidcConfig}>
        <OIDCAuthWrapper>{children}</OIDCAuthWrapper>
      </OIDCProvider>
    );
  },
);
ProductionAuthProvider.displayName = 'ProductionAuthProvider';

/**
 * Wrapper for OIDC provider to adapt to our auth context
 */
const OIDCAuthWrapper = React.memo(({ children }: { children: React.ReactNode }) => {
  const oidcAuth = useOIDCAuth();
  const [user, setUser] = useState<User | null>(null);
  // Note: Location is now handled by LocationCapture component on user interaction

  // Update ApiClient token whenever it changes (including on refresh)
  useEffect(() => {
    if (oidcAuth.user?.access_token) {
      ApiClient.setToken(oidcAuth.user.access_token);
      if (import.meta.env.DEV) {
        console.log('🔄 Token updated in ApiClient');
      }
    }
  }, [oidcAuth.user?.access_token]);

  // Handle token expiring event - manually trigger renewal if needed
  useEffect(() => {
    const handleAccessTokenExpiring = () => {
      if (import.meta.env.DEV) {
        console.log('⏰ Access token expiring soon, renewing...');
      }
      // The automaticSilentRenew should handle this, but we can also force it
      oidcAuth.signinSilent().catch((err) => {
        console.error('Failed to silently renew token:', err);
      });
    };

    // Listen for token expiring events
    if (oidcAuth.events) {
      oidcAuth.events.addAccessTokenExpiring(handleAccessTokenExpiring);
      return () => {
        oidcAuth.events.removeAccessTokenExpiring(handleAccessTokenExpiring);
      };
    }
  }, [oidcAuth]);

  // Set up auth error handler to refresh token on 401 errors
  useEffect(() => {
    let isRefreshing = false;

    ApiClient.setAuthErrorHandler(() => {
      // Prevent multiple simultaneous refresh attempts
      if (isRefreshing) {
        return;
      }
      isRefreshing = true;

      if (import.meta.env.DEV) {
        console.log('🔄 Auth error detected, attempting silent token refresh...');
      }

      oidcAuth
        .signinSilent()
        .catch((err) => {
          console.error('Failed to refresh token after auth error:', err);

          // Clear all auth storage to prevent stale token issues
          clearAuthStorage();

          // If silent refresh fails, redirect to login
          if (import.meta.env.DEV) {
            console.log(
              '🔒 Silent refresh failed, clearing auth storage and redirecting to login...',
            );
          }

          // Use removeUser to properly clean up OIDC state
          oidcAuth.removeUser().finally(() => {
            oidcAuth.signinRedirect();
          });
        })
        .finally(() => {
          isRefreshing = false;
        });
    });

    return () => {
      ApiClient.setAuthErrorHandler(() => {});
    };
  }, [oidcAuth]);

  useEffect(() => {
    if (oidcAuth.error) {
      console.error('OIDC Authentication Error:', oidcAuth.error);

      // Clear stale auth data on OIDC errors (e.g., invalid tokens from previous deployment)
      const errorMessage = oidcAuth.error.message?.toLowerCase() || '';
      if (
        errorMessage.includes('invalid') ||
        errorMessage.includes('expired') ||
        errorMessage.includes('token') ||
        errorMessage.includes('session') ||
        errorMessage.includes('refresh')
      ) {
        if (import.meta.env.DEV) {
          console.log(
            '🧹 OIDC error indicates stale auth data, clearing storage and redirecting to login...',
          );
        }
        clearAuthStorage();

        // Remove user from OIDC state and redirect to login
        oidcAuth
          .removeUser()
          .then(() => {
            // Small delay to ensure storage is cleared before redirect
            setTimeout(() => {
              oidcAuth.signinRedirect();
            }, 100);
          })
          .catch(() => {
            // If removeUser fails, still try to redirect
            setTimeout(() => {
              oidcAuth.signinRedirect();
            }, 100);
          });
      }
    }

    if (oidcAuth.user) {
      const newUser: User = {
        id: oidcAuth.user.profile.sub!,
        email: oidcAuth.user.profile.email!,
        username: oidcAuth.user.profile.preferred_username,
        name: oidcAuth.user.profile.name,
        roles: (oidcAuth.user.profile as { realm_access?: { roles?: string[] } })
          .realm_access?.roles || ['user'],
        isDevMode: false,
      };
      setUser(newUser);

      if (import.meta.env.DEV) {
        console.log('🔒 User authenticated via OIDC:', {
          id: oidcAuth.user.profile.sub,
          email: oidcAuth.user.profile.email,
        });
      }
    } else {
      setUser(null);
      clearStoredLocation(); // Clear location data on logout (frontend cleanup)
      // Clear token from ApiClient
      ApiClient.setToken(null);
      // Note: Location clearing also handled by backend on logout
    }
  }, [oidcAuth]);

  // Location is now handled by LocationCapture component

  const login = useCallback(() => oidcAuth.signinRedirect(), [oidcAuth]);
  const logout = useCallback(() => {
    // Clear all auth storage before redirecting to logout
    clearAuthStorage();
    oidcAuth.signoutRedirect();
  }, [oidcAuth]);
  const signinRedirect = useCallback(() => oidcAuth.signinRedirect(), [oidcAuth]);

  const contextValue: AuthContextType = useMemo(() => {
    const authState = {
      user,
      isAuthenticated: !!oidcAuth.user,
      isLoading: oidcAuth.isLoading,
      login,
      logout,
      signinRedirect,
      error: oidcAuth.error ? new Error(oidcAuth.error.message) : null,
    };

    // Auth context state updated

    return authState;
  }, [
    user,
    oidcAuth.user,
    oidcAuth.isLoading,
    oidcAuth.error,
    login,
    logout,
    signinRedirect,
  ]);

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
});
OIDCAuthWrapper.displayName = 'OIDCAuthWrapper';

/**
 * Main Auth Provider - chooses development or production mode
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (authConfig.bypassAuth) {
    return <DevAuthProvider>{children}</DevAuthProvider>;
  }

  return <ProductionAuthProvider>{children}</ProductionAuthProvider>;
}
