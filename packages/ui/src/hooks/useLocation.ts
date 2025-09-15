/**
 * Location services hook for fraud detection
 * Captures user location via browser Geolocation API
 */

import { useState, useCallback, useEffect } from 'react';

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: number;
}

export interface LocationError {
  code: number;
  message: string;
}

export interface UseLocationResult {
  location: LocationData | null;
  error: LocationError | null;
  isLoading: boolean;
  isSupported: boolean;
  requestLocation: () => void;
  clearLocation: () => void;
}

const LOCATION_TIMEOUT = 15000; // 15 seconds
const LOCATION_MAX_AGE = 300000; // 5 minutes

/**
 * Hook for managing user location
 */
export function useLocation(): UseLocationResult {
  const [location, setLocation] = useState<LocationData | null>(null);
  const [error, setError] = useState<LocationError | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Check if geolocation is supported
  const isSupported = 'geolocation' in navigator;

  const clearLocation = useCallback(() => {
    setLocation(null);
    setError(null);
  }, []);

  const requestLocation = useCallback(() => {
    if (!isSupported) {
      setError({
        code: 0,
        message: 'Geolocation is not supported by this browser',
      });
      return;
    }

    setIsLoading(true);
    setError(null);

    // eslint-disable-next-line no-undef
    const options: PositionOptions = {
      enableHighAccuracy: true,
      timeout: LOCATION_TIMEOUT,
      maximumAge: LOCATION_MAX_AGE,
    };

    // eslint-disable-next-line no-undef
    const handleSuccess = (position: GeolocationPosition) => {
      const locationData: LocationData = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
      };

      setLocation(locationData);
      setError(null);
      setIsLoading(false);

      if (import.meta.env.DEV) {
        console.log('📍 Location captured:', {
          lat: locationData.latitude.toFixed(6),
          lng: locationData.longitude.toFixed(6),
          accuracy: `${locationData.accuracy}m`,
        });
      }
    };

    // eslint-disable-next-line no-undef
    const handleError = (err: GeolocationPositionError) => {
      let message: string;

      switch (err.code) {
        case err.PERMISSION_DENIED:
          message = 'Location access denied by user';
          break;
        case err.POSITION_UNAVAILABLE:
          message = 'Location information is unavailable';
          break;
        case err.TIMEOUT:
          message = 'Location request timed out';
          break;
        default:
          message = 'An unknown error occurred while retrieving location';
          break;
      }

      const locationError: LocationError = {
        code: err.code,
        message,
      };

      setError(locationError);
      setLocation(null);
      setIsLoading(false);

      if (import.meta.env.DEV) {
        console.warn('📍 Location error:', locationError);
      }
    };

    navigator.geolocation.getCurrentPosition(handleSuccess, handleError, options);
  }, [isSupported]);

  return {
    location,
    error,
    isLoading,
    isSupported,
    requestLocation,
    clearLocation,
  };
}

/**
 * Hook for automatic location capture on component mount
 */
export function useLocationOnMount(autoRequest = true): UseLocationResult {
  const location = useLocation();

  useEffect(() => {
    if (autoRequest && location.isSupported && !location.location && !location.error) {
      location.requestLocation();
    }
  }, [autoRequest, location]);

  return location;
}

/**
 * Create location headers for API requests
 */
export function createLocationHeaders(
  location: LocationData | null,
): Record<string, string> {
  if (!location) {
    return {};
  }

  return {
    'X-User-Latitude': location.latitude.toString(),
    'X-User-Longitude': location.longitude.toString(),
    'X-User-Location-Accuracy': location.accuracy.toString(),
  };
}

/**
 * Get stored location from localStorage (for persistence across sessions)
 */
export function getStoredLocation(): LocationData | null {
  try {
    const stored = localStorage.getItem('user-location');
    if (!stored) return null;

    const parsed = JSON.parse(stored);

    // Check if location is stale (older than 1 hour)
    const now = Date.now();
    const maxAge = 60 * 60 * 1000; // 1 hour

    if (now - parsed.timestamp > maxAge) {
      localStorage.removeItem('user-location');
      return null;
    }

    return parsed;
  } catch {
    localStorage.removeItem('user-location');
    return null;
  }
}

/**
 * Store location in localStorage for persistence
 */
export function storeLocation(location: LocationData): void {
  try {
    localStorage.setItem('user-location', JSON.stringify(location));
  } catch (error) {
    console.warn('Failed to store location:', error);
  }
}

/**
 * Clear stored location
 */
export function clearStoredLocation(): void {
  try {
    localStorage.removeItem('user-location');
  } catch (error) {
    console.warn('Failed to clear stored location:', error);
  }
}
