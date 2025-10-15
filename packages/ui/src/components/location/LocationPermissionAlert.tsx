/**
 * Location Permission Alert Component
 * Shows an alert on alert rules page when location permissions aren't granted
 */

import { useEffect, useState } from 'react';
import { Alert, AlertDescription } from '../atoms/alert/alert';
import { Button } from '../atoms/button/button';
import { MapPinOff, ChevronDown, ChevronUp } from 'lucide-react';
import { checkLocationPermission } from '../../services/geolocation';
import { useLocationContext } from './LocationProvider';

interface LocationPermissionAlertProps {
  className?: string;
}

/**
 * Alert component that shows when location permissions are not granted
 * Only displays on alert rules page to inform about location-based alerts
 */
export function LocationPermissionAlert({ className }: LocationPermissionAlertProps) {
  const [permissionState, setPermissionState] = useState<
    'granted' | 'denied' | 'prompt' | null
  >(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);

  // Use location context to check if location updates are actually working
  const locationContext = useLocationContext();
  const isLocationWorking =
    locationContext?.isActive && locationContext?.updateCount > 0;

  useEffect(() => {
    const checkPermissions = async () => {
      try {
        const permission = await checkLocationPermission();
        setPermissionState(permission);
      } catch (error) {
        console.warn('Failed to check location permissions:', error);
        // Assume permissions not granted if check fails
        setPermissionState('denied');
      } finally {
        setIsLoading(false);
      }
    };

    // Single check on mount - component will re-render when locationContext updates
    checkPermissions();
  }, []);

  // Don't show anything while loading, if permissions are granted, or if location is actually working
  if (isLoading || permissionState === 'granted' || isLocationWorking) {
    return null;
  }

  const toggleExpanded = () => setIsExpanded(!isExpanded);

  // Show compact alert when permissions are denied, prompt, or unknown
  return (
    <Alert variant="destructive" className={className}>
      <MapPinOff className="h-4 w-4" />
      <AlertDescription>
        <div className="flex items-center justify-between">
          <span className="font-medium">Location-based alerts unavailable</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleExpanded}
            className="text-red-600 hover:text-red-700 hover:bg-red-50 p-1 h-auto"
          >
            Learn More
            {isExpanded ? (
              <ChevronUp className="h-3 w-3 ml-1" />
            ) : (
              <ChevronDown className="h-3 w-3 ml-1" />
            )}
          </Button>
        </div>

        {isExpanded && (
          <div className="mt-3 text-sm border-t pt-3 border-red-200">
            <p className="mb-2">
              Location permissions haven't been granted. Rules that depend on location
              data (like "transactions outside usual area") won't work properly.
              {permissionState === 'prompt'
                ? ' Your browser will ask for permission when needed.'
                : ' You can enable location access in your browser settings.'}
            </p>
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}
