/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCurrentUser } from '../user';
import { currentUserService } from '../../services/user';

vi.mock('../../services/user');

describe('useCurrentUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load stored user', async () => {
    const mockUser = { id: '1', name: 'Test User', email: 'test@example.com' };
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(mockUser as any);

    const { result } = renderHook(() => useCurrentUser());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.error).toBeNull();
    expect(currentUserService.getCurrentUser).toHaveBeenCalled();
  });

  it('should initialize demo user when no stored user', async () => {
    const mockDemoUser = { id: 'demo', name: 'Demo User', email: 'demo@example.com' };
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(null);
    vi.mocked(currentUserService.initializeDemoUser).mockResolvedValue(
      mockDemoUser as any,
    );

    const { result } = renderHook(() => useCurrentUser());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.user).toEqual(mockDemoUser);
    expect(result.current.error).toBeNull();
    expect(currentUserService.initializeDemoUser).toHaveBeenCalled();
  });

  it('should handle initialization error', async () => {
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(null);
    vi.mocked(currentUserService.initializeDemoUser).mockRejectedValue(
      new Error('Init failed'),
    );

    const { result } = renderHook(() => useCurrentUser());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.user).toBeNull();
    expect(result.current.error).toBe('Init failed');
  });

  it('should handle non-Error exceptions', async () => {
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(null);
    vi.mocked(currentUserService.initializeDemoUser).mockRejectedValue('String error');

    const { result } = renderHook(() => useCurrentUser());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.user).toBeNull();
    expect(result.current.error).toBe('Failed to initialize user');
  });

  it('should refresh user', async () => {
    const mockUser = { id: '1', name: 'User' };
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(mockUser as any);

    const { result } = renderHook(() => useCurrentUser());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // Change mock to return different user
    const newUser = { id: '2', name: 'New User' };
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(newUser as any);

    // Call refresh
    await result.current.refreshUser();

    await waitFor(() => expect(result.current.user).toEqual(newUser));
  });

  it('should logout user', async () => {
    const mockUser = { id: '1', name: 'User' };
    vi.mocked(currentUserService.getCurrentUser).mockReturnValue(mockUser as any);

    const { result } = renderHook(() => useCurrentUser());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toEqual(mockUser);

    // Logout
    result.current.logout();

    await waitFor(() => {
      expect(currentUserService.clearCurrentUser).toHaveBeenCalled();
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });
});
