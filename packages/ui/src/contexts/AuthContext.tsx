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
import type { User, AuthContextType } from '../types/auth';
import { DEV_USER } from '../constants/auth';
import {
  useLocationOnMount,
  storeLocation,
  clearStoredLocation,
} from '../hooks/useLocation';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Development Auth Provider - bypasses OIDC
 */
const DevAuthProvider = React.memo(({ children }: { children: React.ReactNode }) => {
  const [user] = useState<User>(DEV_USER);
  const { location } = useLocationOnMount(true); // Auto-request location in dev mode

  // Store location when captured
  useEffect(() => {
    if (location) {
      storeLocation(location);
      if (import.meta.env.DEV) {
        console.log('📍 Development mode - location captured for fraud detection');
      }
    }
  }, [location]);

  const login = useCallback(() => {
    if (import.meta.env.DEV) {
      console.log('🔓 Dev mode: login() called - already authenticated');
    }
  }, []);

  const logout = useCallback(() => {
    if (import.meta.env.DEV) {
      console.log('🔓 Dev mode: logout() called - staying authenticated');
    }
    clearStoredLocation(); // Clear location data on logout
  }, []);

  const signinRedirect = useCallback(() => {
    if (import.meta.env.DEV) {
      console.log('🔓 Dev mode: signinRedirect() called - already authenticated');
    }
  }, []);

  const contextValue: AuthContextType = useMemo(
    () => ({
      user,
      isAuthenticated: true,
      isLoading: false,
      login,
      logout,
      signinRedirect,
      error: null,
    }),
    [user, login, logout, signinRedirect],
  );

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log('🔓 Development auth provider initialized');
    }
  }, []);

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
});
DevAuthProvider.displayName = 'DevAuthProvider';

/**
 * Production OIDC Auth Provider
 */
const ProductionAuthProvider = React.memo(
  ({ children }: { children: React.ReactNode }) => {
    const oidcConfig = useMemo(
      () => ({
        authority: authConfig.keycloak.authority,
        client_id: authConfig.keycloak.clientId,
        redirect_uri: authConfig.keycloak.redirectUri,
        post_logout_redirect_uri: authConfig.keycloak.postLogoutRedirectUri,
        response_type: 'code',
        scope: 'openid profile email',
        automaticSilentRenew: true,
        includeIdTokenInSilentRenew: true,
      }),
      [],
    );

    useEffect(() => {
      if (import.meta.env.DEV) {
        console.log('🔒 Production OIDC config:', {
          authority: oidcConfig.authority,
          client_id: oidcConfig.client_id,
          redirect_uri: oidcConfig.redirect_uri,
        });
      }
    }, [oidcConfig]);

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
  const [hasRequestedLocation, setHasRequestedLocation] = useState(false);
  const { location, requestLocation } = useLocationOnMount(false); // Don't auto-request, we'll do it manually on login

  useEffect(() => {
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

      // Request location on successful login (only once per session)
      if (!hasRequestedLocation) {
        requestLocation();
        setHasRequestedLocation(true);
      }

      if (import.meta.env.DEV) {
        console.log('🔒 User authenticated via OIDC:', {
          id: oidcAuth.user.profile.sub,
          email: oidcAuth.user.profile.email,
        });
      }
    } else {
      setUser(null);
      setHasRequestedLocation(false);
      clearStoredLocation(); // Clear location data on logout
    }
  }, [oidcAuth.user, hasRequestedLocation, requestLocation]);

  // Store location when captured
  useEffect(() => {
    if (location && user) {
      storeLocation(location);
      if (import.meta.env.DEV) {
        console.log('📍 Production mode - location captured for fraud detection');
      }
    }
  }, [location, user]);

  const login = useCallback(() => oidcAuth.signinRedirect(), [oidcAuth]);
  const logout = useCallback(() => oidcAuth.signoutRedirect(), [oidcAuth]);
  const signinRedirect = useCallback(() => oidcAuth.signinRedirect(), [oidcAuth]);

  const contextValue: AuthContextType = useMemo(
    () => ({
      user,
      isAuthenticated: !!oidcAuth.user,
      isLoading: oidcAuth.isLoading,
      login,
      logout,
      signinRedirect,
      error: oidcAuth.error ? new Error(oidcAuth.error.message) : null,
    }),
    [
      user,
      oidcAuth.user,
      oidcAuth.isLoading,
      oidcAuth.error,
      login,
      logout,
      signinRedirect,
    ],
  );

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
