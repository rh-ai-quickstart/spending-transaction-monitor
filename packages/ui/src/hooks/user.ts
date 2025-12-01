import { useState, useEffect } from 'react';
import { currentUserService } from '../services/user';
import type { CurrentUser, UseCurrentUserResult } from '../schemas/user';

export function useCurrentUser(): UseCurrentUserResult {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const initializeUser = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // First check if user is already stored locally
      const storedUser = currentUserService.getCurrentUser();
      if (storedUser) {
        setUser(storedUser);
        setIsLoading(false);
        return;
      }

      // If no stored user, initialize demo user (fetches from API or fallback)
      const initializedUser = await currentUserService.initializeDemoUser();
      setUser(initializedUser);
    } catch (err) {
      console.error('Error initializing user:', err);
      setError(err instanceof Error ? err.message : 'Failed to initialize user');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    await initializeUser();
  };

  const logout = () => {
    currentUserService.clearCurrentUser();
    setUser(null);
    setError(null);
  };

  useEffect(() => {
    initializeUser();
  }, []);

  return {
    user,
    isLoading,
    error,
    refreshUser,
    logout,
  };
}
