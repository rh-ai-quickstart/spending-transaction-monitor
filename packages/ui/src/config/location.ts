/**
 * Location service configuration
 * Controls periodic location updates for fraud detection
 */

export interface LocationConfig {
  updateIntervalMs: number;
  enablePeriodicUpdates: boolean;
  maxRetryAttempts: number;
  retryDelayMs: number;
}

// Default to 15 minutes (15 * 60 * 1000 = 900000ms)
const DEFAULT_UPDATE_INTERVAL_MS = 15 * 60 * 1000;

// Parse the interval from environment variable (in minutes, convert to ms)
const getUpdateInterval = (): number => {
  const envInterval = import.meta.env.VITE_LOCATION_UPDATE_INTERVAL_MINUTES;
  if (!envInterval) return DEFAULT_UPDATE_INTERVAL_MS;
  
  const intervalMinutes = parseInt(envInterval, 10);
  
  // Validation: must be between 5 minutes and 2 hours for security/battery reasons
  if (isNaN(intervalMinutes) || intervalMinutes < 5 || intervalMinutes > 120) {
    console.warn(
      `⚠️ Invalid VITE_LOCATION_UPDATE_INTERVAL_MINUTES (${envInterval}). ` +
      `Must be between 5-120 minutes. Using default: ${DEFAULT_UPDATE_INTERVAL_MS / (60 * 1000)} minutes`
    );
    return DEFAULT_UPDATE_INTERVAL_MS;
  }
  
  return intervalMinutes * 60 * 1000;
};

export const locationConfig: LocationConfig = {
  updateIntervalMs: getUpdateInterval(),
  enablePeriodicUpdates: import.meta.env.VITE_ENABLE_PERIODIC_LOCATION_UPDATES !== 'false',
  maxRetryAttempts: parseInt(import.meta.env.VITE_LOCATION_MAX_RETRY_ATTEMPTS || '3', 10),
  retryDelayMs: parseInt(import.meta.env.VITE_LOCATION_RETRY_DELAY_MS || '5000', 10),
};

// Log configuration for debugging (only in development)
if (import.meta.env.DEV) {
  console.log('🗺️ Location Configuration:', {
    updateIntervalMinutes: Math.round(locationConfig.updateIntervalMs / (60 * 1000)),
    enablePeriodicUpdates: locationConfig.enablePeriodicUpdates,
    maxRetryAttempts: locationConfig.maxRetryAttempts,
    retryDelayMs: locationConfig.retryDelayMs,
  });
  
  if (locationConfig.enablePeriodicUpdates) {
    console.log(
      `🕐 Periodic location updates enabled: every ${Math.round(locationConfig.updateIntervalMs / (60 * 1000))} minutes`
    );
  } else {
    console.log('🚫 Periodic location updates disabled');
  }
}
