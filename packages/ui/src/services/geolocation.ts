/**
 * Geolocation service with proper browser integration
 * Based on MDN Geolocation API: https://developer.mozilla.org/en-US/docs/Web/API/Navigator/geolocation
 */

export interface UserLocation {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp?: number;
}

/**
 * Get current location using navigator.geolocation.getCurrentPosition()
 * This will ALWAYS prompt the browser for permission if not already granted
 */
export function getCurrentLocation(): Promise<UserLocation> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by your browser.'));
      return;
    }

    console.log('🌍 Requesting geolocation permission...');

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        console.log('✅ Location permission granted and coordinates received');
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          timestamp: pos.timestamp,
        });
      },
      (err) => {
        console.error('❌ Geolocation error:', err);
        reject(new Error(err.message));
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0, // Always get fresh location
      },
    );
  });
}

/**
 * Watch location changes continuously
 */
export function watchLocation(
  onSuccess: (loc: UserLocation) => void,
  onError?: (err: Error) => void,
): number {
  if (!navigator.geolocation) {
    onError?.(new Error('Geolocation is not supported by your browser.'));
    return -1;
  }

  const id = navigator.geolocation.watchPosition(
    (pos) => {
      onSuccess({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        timestamp: pos.timestamp,
      });
    },
    (err) => {
      onError?.(new Error(err.message));
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    },
  );
  return id;
}

/**
 * Clear location watching
 */
export function clearWatch(id: number) {
  if (id !== -1) {
    navigator.geolocation.clearWatch(id);
  }
}

/**
 * Check current permission state
 */
export async function checkLocationPermission(): Promise<
  'granted' | 'denied' | 'prompt'
> {
  if ('permissions' in navigator) {
    const permission = await navigator.permissions.query({ name: 'geolocation' });
    return permission.state;
  }
  return 'prompt'; // Default if permissions API not available
}
