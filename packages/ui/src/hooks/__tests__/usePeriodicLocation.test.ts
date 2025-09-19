/**
 * Tests for usePeriodicLocation hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePeriodicLocation } from '../usePeriodicLocation';
import * as geolocationService from '@/services/geolocation';
import { useAuth } from '@/hooks/useAuth';
import type { AuthContextType } from '@/types/auth';

// Mock the geolocation service
vi.mock('@/services/geolocation', () => ({
  getCurrentLocation: vi.fn(),
}));

// Mock the auth hook
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
  })),
}));

// Mock the location config
vi.mock('@/config/location', () => ({
  locationConfig: {
    updateIntervalMs: 5000, // 5 seconds for testing
    enablePeriodicUpdates: true,
    maxRetryAttempts: 2,
    retryDelayMs: 1000,
  },
}));

// Mock fetch
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Mock timers
vi.useFakeTimers();

describe('usePeriodicLocation', () => {
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    accuracy: 10,
    timestamp: Date.now(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(geolocationService.getCurrentLocation).mockResolvedValue(mockLocation);
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
    // Default to authenticated
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: true } as AuthContextType);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('should initialize with default state when not authenticated', () => {
    // Mock unauthenticated state
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: false } as AuthContextType);
    
    const { result } = renderHook(() => usePeriodicLocation());

    expect(result.current.isActive).toBe(false);
    expect(result.current.lastUpdate).toBeNull();
    expect(result.current.updateCount).toBe(0);
    expect(result.current.lastError).toBeNull();
    expect(result.current.nextUpdateIn).toBe(0);
  });

  it('should auto-start when authenticated and config enabled', async () => {
    const { result } = renderHook(() => usePeriodicLocation());

    // Should auto-start
    await act(async () => {
      vi.advanceTimersByTime(100); // Allow for useEffect to run
    });

    expect(result.current.isActive).toBe(true);
    expect(geolocationService.getCurrentLocation).toHaveBeenCalled();
  });

  it('should perform location updates at configured intervals', async () => {
    const { result } = renderHook(() => usePeriodicLocation());

    await act(async () => {
      vi.advanceTimersByTime(100); // Auto-start
    });

    expect(result.current.updateCount).toBe(1);

    // Advance time to trigger next update
    await act(async () => {
      vi.advanceTimersByTime(5000); // Match updateIntervalMs
    });

    expect(result.current.updateCount).toBe(2);
    expect(geolocationService.getCurrentLocation).toHaveBeenCalledTimes(2);
  });

  it('should handle location errors with retry logic', async () => {
    vi.mocked(geolocationService.getCurrentLocation)
      .mockRejectedValueOnce(new Error('Location unavailable'))
      .mockResolvedValueOnce(mockLocation);

    const { result } = renderHook(() => usePeriodicLocation());

    await act(async () => {
      vi.advanceTimersByTime(100); // Auto-start
    });

    expect(result.current.lastError).toBe('Location unavailable');

    // Advance time for retry
    await act(async () => {
      vi.advanceTimersByTime(1000); // Match retryDelayMs
    });

    expect(result.current.lastError).toBeNull();
    expect(result.current.updateCount).toBe(1);
  });

  it('should stop periodic updates when manually stopped and not auto-restart', async () => {
    const { result } = renderHook(() => usePeriodicLocation());

    await act(async () => {
      vi.advanceTimersByTime(100); // Auto-start
    });

    expect(result.current.isActive).toBe(true);

    // Manually stop
    act(() => {
      result.current.stop(true);
    });

    expect(result.current.isActive).toBe(false);

    // Advance timers - should NOT auto-restart because manually stopped
    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    // Should remain stopped because it was manually stopped
    expect(result.current.isActive).toBe(false);
  });

  it('should force immediate location update', async () => {
    const { result } = renderHook(() => usePeriodicLocation());

    await act(async () => {
      vi.advanceTimersByTime(100); // Auto-start
    });

    const initialCount = result.current.updateCount;

    await act(async () => {
      await result.current.forceUpdate();
    });

    expect(result.current.updateCount).toBe(initialCount + 1);
    expect(geolocationService.getCurrentLocation).toHaveBeenCalledTimes(2);
  });

  it('should stop when user becomes unauthenticated', async () => {
    const { result, rerender } = renderHook(() => usePeriodicLocation());

    await act(async () => {
      vi.advanceTimersByTime(100); // Auto-start
    });

    expect(result.current.isActive).toBe(true);

    // Mock user becoming unauthenticated
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: false } as AuthContextType);
    
    // Rerender to trigger useEffect
    rerender();

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.isActive).toBe(false);
  });

  it('should send correct headers to backend', async () => {
    renderHook(() => usePeriodicLocation());

    await act(async () => {
      vi.advanceTimersByTime(100); // Auto-start
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/users/location', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Latitude': mockLocation.latitude.toString(),
        'X-User-Longitude': mockLocation.longitude.toString(),
        'X-User-Location-Accuracy': mockLocation.accuracy.toString(),
      },
      body: JSON.stringify({
        location_consent_given: true,
        last_app_location_latitude: mockLocation.latitude,
        last_app_location_longitude: mockLocation.longitude,
        last_app_location_accuracy: mockLocation.accuracy,
      }),
    });
  });
});
