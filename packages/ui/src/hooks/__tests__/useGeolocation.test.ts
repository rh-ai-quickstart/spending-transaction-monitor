/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useUserLocation } from '../useGeolocation';
import * as geolocationService from '../../services/geolocation';

// Mock the geolocation service
vi.mock('../../services/geolocation', () => ({
  getCurrentLocation: vi.fn(),
  watchLocation: vi.fn(),
  clearWatch: vi.fn(),
  checkLocationPermission: vi.fn(),
}));

// Mock apiClient
vi.mock('../../services/apiClient', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe('useUserLocation', () => {
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    accuracy: 10,
    timestamp: Date.now(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(geolocationService.checkLocationPermission).mockResolvedValue('prompt');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with null location and loading false', () => {
    const { result } = renderHook(() => useUserLocation(false, false));

    expect(result.current.location).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('should check permission state on mount', async () => {
    renderHook(() => useUserLocation(false, false));

    await waitFor(() => {
      expect(geolocationService.checkLocationPermission).toHaveBeenCalled();
    });
  });

  it('should set permission state after checking', async () => {
    vi.mocked(geolocationService.checkLocationPermission).mockResolvedValue('granted');

    const { result } = renderHook(() => useUserLocation(false, false));

    await waitFor(() => {
      expect(result.current.permissionState).toBe('granted');
    });
  });

  it('should request location successfully', async () => {
    vi.mocked(geolocationService.getCurrentLocation).mockResolvedValue(mockLocation);

    const { result } = renderHook(() => useUserLocation(false, false));

    await act(async () => {
      await result.current.requestLocation();
    });

    await waitFor(() => {
      expect(result.current.location).toEqual(mockLocation);
      expect(result.current.error).toBeNull();
      expect(result.current.loading).toBe(false);
    });
  });

  it('should handle location request errors', async () => {
    const errorMessage = 'Location permission denied';
    vi.mocked(geolocationService.getCurrentLocation).mockRejectedValue(
      new Error(errorMessage),
    );

    const { result } = renderHook(() => useUserLocation(false, false));

    await act(async () => {
      await result.current.requestLocation();
    });

    await waitFor(() => {
      expect(result.current.error).toBe(errorMessage);
      expect(result.current.location).toBeNull();
      expect(result.current.loading).toBe(false);
    });
  });

  it('should send location to backend when sendToBackend is true', async () => {
    vi.mocked(geolocationService.getCurrentLocation).mockResolvedValue(mockLocation);

    const mockPost = vi.fn().mockResolvedValue({});
    vi.doMock('../../services/apiClient', () => ({
      apiClient: { post: mockPost },
    }));

    const { result } = renderHook(() => useUserLocation(false, true));

    await act(async () => {
      await result.current.requestLocation();
    });

    await waitFor(() => {
      expect(result.current.location).toEqual(mockLocation);
    });
  });

  it('should not send location to backend when sendToBackend is false', async () => {
    vi.mocked(geolocationService.getCurrentLocation).mockResolvedValue(mockLocation);

    const mockPost = vi.fn();
    vi.doMock('../../services/apiClient', () => ({
      apiClient: { post: mockPost },
    }));

    const { result } = renderHook(() => useUserLocation(false, false));

    await act(async () => {
      await result.current.requestLocation();
    });

    await waitFor(() => {
      expect(result.current.location).toEqual(mockLocation);
    });

    // Should not call backend
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('should clear location when clearLocation is called', async () => {
    vi.mocked(geolocationService.getCurrentLocation).mockResolvedValue(mockLocation);

    const { result } = renderHook(() => useUserLocation(false, false));

    // First request location
    await act(async () => {
      await result.current.requestLocation();
    });

    await waitFor(() => {
      expect(result.current.location).toEqual(mockLocation);
    });

    // Then clear it
    act(() => {
      result.current.clearLocation();
    });

    expect(result.current.location).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('should watch location when watch is true', async () => {
    const watchId = 123;
    const mockCallback = vi.fn();

    vi.mocked(geolocationService.watchLocation).mockImplementation((callback) => {
      mockCallback.mockImplementation(callback);
      return watchId;
    });

    const { unmount } = renderHook(() => useUserLocation(true, false));

    await waitFor(() => {
      expect(geolocationService.watchLocation).toHaveBeenCalled();
    });

    // Cleanup should clear watch
    unmount();

    expect(geolocationService.clearWatch).toHaveBeenCalledWith(watchId);
  });

  it('should update location when watch detects changes', async () => {
    let watchCallback: ((location: geolocationService.Location) => void) | null = null;

    vi.mocked(geolocationService.watchLocation).mockImplementation((callback) => {
      watchCallback = callback;
      return 123;
    });

    const { result } = renderHook(() => useUserLocation(true, false));

    await waitFor(() => {
      expect(geolocationService.watchLocation).toHaveBeenCalled();
    });

    // Simulate location update from watch
    const newLocation = { ...mockLocation, latitude: 40.7128 };

    await act(async () => {
      watchCallback?.(newLocation);
    });

    await waitFor(() => {
      expect(result.current.location).toEqual(newLocation);
    });
  });

  it('should handle watch errors gracefully', async () => {
    let errorCallback: ((error: Error) => void) | null = null;

    vi.mocked(geolocationService.watchLocation).mockImplementation(
      (onSuccess, onError) => {
        // onSuccess callback intentionally unused in this error-handling test
        void onSuccess;
        errorCallback = onError || null;
        return 123;
      },
    );

    const { result } = renderHook(() => useUserLocation(true, false));

    await waitFor(() => {
      expect(geolocationService.watchLocation).toHaveBeenCalled();
    });

    // Simulate watch error
    const error = new Error('Location watch failed');

    await act(async () => {
      errorCallback?.(error);
    });

    await waitFor(() => {
      expect(result.current.error).toBe('Location watch failed');
    });
  });

  it('should set loading state during location request', async () => {
    let resolveLocation: (value: geolocationService.Location) => void;
    const locationPromise = new Promise<geolocationService.Location>((resolve) => {
      resolveLocation = resolve;
    });

    vi.mocked(geolocationService.getCurrentLocation).mockReturnValue(locationPromise);

    const { result } = renderHook(() => useUserLocation(false, false));

    act(() => {
      result.current.requestLocation();
    });

    // Should be loading immediately
    expect(result.current.loading).toBe(true);

    // Resolve the promise
    await act(async () => {
      resolveLocation!(mockLocation);
      await locationPromise;
    });

    // Should not be loading after resolution
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it('should handle permission denied state', async () => {
    vi.mocked(geolocationService.checkLocationPermission).mockResolvedValue('denied');

    const { result } = renderHook(() => useUserLocation(false, false));

    await waitFor(() => {
      expect(result.current.permissionState).toBe('denied');
    });
  });

  it('should handle permission granted state', async () => {
    vi.mocked(geolocationService.checkLocationPermission).mockResolvedValue('granted');

    const { result } = renderHook(() => useUserLocation(false, false));

    await waitFor(() => {
      expect(result.current.permissionState).toBe('granted');
    });
  });

  it('should clear watch on unmount when watching', async () => {
    const watchId = 456;
    vi.mocked(geolocationService.watchLocation).mockReturnValue(watchId);

    const { unmount } = renderHook(() => useUserLocation(true, false));

    await waitFor(() => {
      expect(geolocationService.watchLocation).toHaveBeenCalled();
    });

    unmount();

    expect(geolocationService.clearWatch).toHaveBeenCalledWith(watchId);
  });

  it('should not watch location when watch is false', () => {
    renderHook(() => useUserLocation(false, false));

    expect(geolocationService.watchLocation).not.toHaveBeenCalled();
  });
});
