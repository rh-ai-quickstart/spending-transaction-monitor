/**
 * LocationStatus component for debugging/admin use
 * Displays location service status in development mode
 */

import { useLocationContext } from './LocationProvider';

export function LocationStatus() {
  const {
    isActive,
    lastUpdate,
    updateCount,
    lastError,
    nextUpdateIn,
    forceUpdate,
  } = useLocationContext();

  const formatCountdown = (seconds: number): string => {
    if (seconds <= 0) return 'Now';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  // Only show in development or for debugging
  if (!import.meta.env.DEV) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-lg text-xs max-w-xs">
      <div className="font-semibold mb-2 text-gray-900 dark:text-gray-100">
        📍 Location Service
      </div>
      
      <div className="space-y-1 text-gray-600 dark:text-gray-400">
        <div>Status: {isActive ? '🟢 Active' : '🔴 Inactive'}</div>
        {lastUpdate && (
          <div>Last: {lastUpdate.toLocaleTimeString()}</div>
        )}
        <div>Updates: {updateCount}</div>
        {isActive && nextUpdateIn > 0 && (
          <div>Next: {formatCountdown(nextUpdateIn)}</div>
        )}
        {lastError && (
          <div className="text-red-500 dark:text-red-400">
            Error: {lastError}
          </div>
        )}
      </div>

      <button
        onClick={() => forceUpdate()}
        className="mt-2 px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition-colors"
      >
        Update Now
      </button>
    </div>
  );
}
