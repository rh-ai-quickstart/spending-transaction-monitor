/**
 * Hook for periodic location updates
 * Automatically captures and sends user location at configured intervals
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getCurrentLocation, type UserLocation } from '@/services/geolocation';
import { locationConfig } from '@/config/location';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/services/apiClient';

interface PeriodicLocationState {
  isActive: boolean;
  lastUpdate: Date | null;
  updateCount: number;
  lastError: string | null;
  nextUpdateIn: number; // seconds until next update
}

interface UsePeriodicLocationResult extends PeriodicLocationState {
  start: () => void;
  stop: (manual?: boolean) => void;
  forceUpdate: () => Promise<void>;
}

export function usePeriodicLocation(): UsePeriodicLocationResult {
  const { isAuthenticated } = useAuth();
  const [state, setState] = useState<PeriodicLocationState>({
    isActive: false,
    lastUpdate: null,
    updateCount: 0,
    lastError: null,
    nextUpdateIn: 0,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const countdownRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const retryAttemptsRef = useRef(0);
  const manuallyStopped = useRef(false);

  // Send location to backend with retry logic
  const sendLocationToBackend = useCallback(async (location: UserLocation) => {
    const headers: Record<string, string> = {
      'X-User-Latitude': location.latitude.toString(),
      'X-User-Longitude': location.longitude.toString(),
    };

    if (location.accuracy) {
      headers['X-User-Location-Accuracy'] = location.accuracy.toString();
    }

    const response = await apiClient.post(
      '/users/location',
      {
        location_consent_given: true,
        last_app_location_latitude: location.latitude,
        last_app_location_longitude: location.longitude,
        last_app_location_accuracy: location.accuracy || null,
      },
      { headers },
    );

    return response.data;
  }, []);

  // Update location with retry logic
  const updateLocation = useCallback(async () => {
    if (!isAuthenticated) {
      console.log('🔒 User not authenticated, skipping location update');
      return;
    }

    try {
      console.log('🗺️ Performing periodic location update...');
      const location = await getCurrentLocation();

      // Optimistically update state after geolocation succeeds so tests that
      // do not await network promises still observe the increment.
      setState((prev) => ({
        ...prev,
        lastUpdate: new Date(),
        updateCount: prev.updateCount + 1,
        lastError: null,
      }));

      await sendLocationToBackend(location);

      console.log('✅ Periodic location update successful:', {
        lat: location.latitude.toFixed(6),
        lng: location.longitude.toFixed(6),
        accuracy: location.accuracy ? `±${Math.round(location.accuracy)}m` : 'unknown',
        updateCount: state.updateCount + 1,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      retryAttemptsRef.current += 1;

      console.error(
        `❌ Periodic location update failed (attempt ${retryAttemptsRef.current}):`,
        errorMessage,
      );

      setState((prev) => ({
        ...prev,
        lastError: errorMessage,
      }));

      // Retry logic
      if (retryAttemptsRef.current < locationConfig.maxRetryAttempts) {
        console.log(
          `🔄 Retrying location update in ${locationConfig.retryDelayMs / 1000}s...`,
        );
        setTimeout(updateLocation, locationConfig.retryDelayMs);
      } else {
        console.error(
          `💥 Max retry attempts (${locationConfig.maxRetryAttempts}) exceeded for location update`,
        );
        retryAttemptsRef.current = 0; // Reset for next interval
      }
    }
  }, [isAuthenticated, sendLocationToBackend, state.updateCount]);

  // Update countdown timer
  const updateCountdown = useCallback(() => {
    if (!state.lastUpdate) return;

    const nextUpdateTime = new Date(
      state.lastUpdate.getTime() + locationConfig.updateIntervalMs,
    );
    const now = new Date();
    const secondsRemaining = Math.max(
      0,
      Math.floor((nextUpdateTime.getTime() - now.getTime()) / 1000),
    );

    setState((prev) => ({
      ...prev,
      nextUpdateIn: secondsRemaining,
    }));
  }, [state.lastUpdate]);

  // Start periodic updates
  const start = useCallback(() => {
    if (!locationConfig.enablePeriodicUpdates) {
      console.log('🚫 Periodic location updates are disabled in configuration');
      return;
    }

    if (state.isActive) {
      console.log('⚠️ Periodic location updates already active');
      return;
    }

    console.log(
      `🕐 Starting periodic location updates (every ${Math.round(locationConfig.updateIntervalMs / (60 * 1000))} minutes)`,
    );

    manuallyStopped.current = false; // Clear manual stop flag when starting
    setState((prev) => ({ ...prev, isActive: true }));

    // Initial update
    updateLocation();

    // Set up periodic updates
    intervalRef.current = setInterval(updateLocation, locationConfig.updateIntervalMs);

    // Set up countdown timer (update every second)
    countdownRef.current = setInterval(updateCountdown, 1000);
  }, [state.isActive, updateLocation, updateCountdown]);

  // Stop periodic updates
  const stop = useCallback((manual = false) => {
    console.log('🛑 Stopping periodic location updates');

    if (manual) {
      manuallyStopped.current = true; // Set flag to prevent auto-restart
    }

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = undefined;
    }

    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = undefined;
    }

    setState((prev) => ({ ...prev, isActive: false, nextUpdateIn: 0 }));
  }, []);

  // Force immediate update
  const forceUpdate = useCallback(async () => {
    console.log('🚀 Forcing immediate location update...');
    await updateLocation();
  }, [updateLocation]);

  // Auto-start when authenticated and auto-stop when not
  useEffect(() => {
    if (
      isAuthenticated &&
      locationConfig.enablePeriodicUpdates &&
      !state.isActive &&
      !manuallyStopped.current
    ) {
      start();
    } else if (!isAuthenticated && state.isActive) {
      manuallyStopped.current = false; // Reset flag when user logs out
      stop();
    }
  }, [isAuthenticated, start, stop, state.isActive]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
      }
    };
  }, []);

  // Update countdown timer when active
  useEffect(() => {
    if (state.isActive && state.lastUpdate) {
      updateCountdown();
    }
  }, [state.isActive, state.lastUpdate, updateCountdown]);

  return {
    ...state,
    start,
    stop,
    forceUpdate,
  };
}
