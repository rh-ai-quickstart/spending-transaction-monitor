/**
 * @vitest-environment jsdom
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider } from '../AuthContext';
import { useAuth } from '../../hooks/useAuth';
import { authConfig } from '../../config/auth';

// Mock the auth config
vi.mock('../../config/auth', () => ({
  authConfig: {
    bypassAuth: true,
    environment: 'development',
    keycloak: {
      authority: 'http://localhost:8080/realms/spending-monitor',
      clientId: 'spending-monitor',
      redirectUri: 'http://localhost:3000',
      postLogoutRedirectUri: 'http://localhost:3000',
    },
  },
}));

// Mock react-oidc-context since we don't need it in dev mode
vi.mock('react-oidc-context', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    signinRedirect: vi.fn(),
    signoutRedirect: vi.fn(),
    error: null,
  }),
}));

// Test component that uses auth
function TestComponent() {
  const auth = useAuth();

  return (
    <div>
      <div data-testid="authenticated">{auth.isAuthenticated ? 'true' : 'false'}</div>
      <div data-testid="loading">{auth.isLoading ? 'true' : 'false'}</div>
      <div data-testid="user-name">{auth.user?.name || 'No user'}</div>
      <div data-testid="user-email">{auth.user?.email || 'No email'}</div>
      <div data-testid="dev-mode">{auth.user?.isDevMode ? 'true' : 'false'}</div>
      <button onClick={auth.login} data-testid="login-btn">
        Login
      </button>
      <button onClick={auth.logout} data-testid="logout-btn">
        Logout
      </button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Development Mode', () => {
    it('should provide authenticated dev user when bypassAuth is true', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
        expect(screen.getByTestId('user-name')).toHaveTextContent('Alex Thompson');
        expect(screen.getByTestId('user-email')).toHaveTextContent(
          'alex.thompson@example.com',
        );
        expect(screen.getByTestId('dev-mode')).toHaveTextContent('true');
      });
    });

    it('should handle login/logout calls gracefully in dev mode', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      const loginBtn = screen.getByTestId('login-btn');
      const logoutBtn = screen.getByTestId('logout-btn');

      // Verify that login/logout methods can be called without throwing errors
      expect(() => {
        loginBtn.click();
      }).not.toThrow();

      expect(() => {
        logoutBtn.click();
      }).not.toThrow();
    });
  });

  describe('useAuth hook', () => {
    it('should throw error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = vi.fn();

      expect(() => render(<TestComponent />)).toThrow(
        'useAuth must be used within an AuthProvider',
      );

      console.error = originalError;
    });
  });

  describe('Auth configuration', () => {
    it('should have correct development configuration', () => {
      expect(authConfig.bypassAuth).toBe(true);
      expect(authConfig.environment).toBe('development');
      expect(authConfig.keycloak.clientId).toBe('spending-monitor');
    });
  });
});
