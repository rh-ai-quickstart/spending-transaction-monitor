/**
 * Location Capture Component
 * Handles user location consent and capture for fraud detection
 */

import { useState, useEffect, useCallback } from 'react';
import { Button } from '../atoms/button/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../atoms/card/card';
import { Alert, AlertDescription } from '../atoms/alert/alert';
import { Badge } from '../atoms/badge/badge';
import { MapPin, Shield, AlertTriangle, CheckCircle2, X } from 'lucide-react';
import {
  useLocation,
  type LocationData,
  type LocationError,
} from '../../hooks/useLocation';

interface LocationCaptureProps {
  onLocationCaptured?: (location: LocationData) => void;
  onLocationDenied?: () => void;
  onLocationError?: (error: LocationError) => void;
  showConsentDialog?: boolean;
  autoRequest?: boolean;
  className?: string;
}

/**
 * Main location capture component with consent handling
 */
export function LocationCapture({
  onLocationCaptured,
  onLocationDenied,
  onLocationError,
  showConsentDialog = true,
  autoRequest = false,
  className,
}: LocationCaptureProps) {
  const { location, error, isLoading, isSupported, requestLocation, clearLocation } =
    useLocation();
  const [showConsent, setShowConsent] = useState(showConsentDialog);
  const [hasUserDeclined, setHasUserDeclined] = useState(false);

  // Handle location capture success
  useEffect(() => {
    if (location && onLocationCaptured) {
      onLocationCaptured(location);
    }
  }, [location, onLocationCaptured]);

  // Handle location errors
  useEffect(() => {
    if (error) {
      if (error.code === 1) {
        // PERMISSION_DENIED
        setHasUserDeclined(true);
        onLocationDenied?.();
      }
      onLocationError?.(error);
    }
  }, [error, onLocationDenied, onLocationError]);

  // Auto-request location if enabled
  useEffect(() => {
    if (
      autoRequest &&
      isSupported &&
      !showConsent &&
      !location &&
      !error &&
      !hasUserDeclined
    ) {
      requestLocation();
    }
  }, [
    autoRequest,
    isSupported,
    showConsent,
    location,
    error,
    hasUserDeclined,
    requestLocation,
  ]);

  const handleGrantConsent = useCallback(() => {
    setShowConsent(false);
    setHasUserDeclined(false);
    requestLocation();
  }, [requestLocation]);

  const handleDenyConsent = useCallback(() => {
    setShowConsent(false);
    setHasUserDeclined(true);
    onLocationDenied?.();
  }, [onLocationDenied]);

  const handleRetryLocation = useCallback(() => {
    clearLocation();
    setHasUserDeclined(false);
    requestLocation();
  }, [clearLocation, requestLocation]);

  if (!isSupported) {
    return (
      <Alert className={className}>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Location services are not supported by your browser. Location-based fraud
          detection will be disabled.
        </AlertDescription>
      </Alert>
    );
  }

  if (showConsent) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-500" />
            Enable Location-Based Security
          </CardTitle>
          <CardDescription>
            Help us protect your account by sharing your location. We'll use this to
            detect suspicious transactions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-muted-foreground space-y-2">
            <p>• Your location is only used for fraud detection</p>
            <p>• Location data is stored securely and encrypted</p>
            <p>• You can disable this feature at any time</p>
            <p>• No location data is shared with third parties</p>
          </div>

          <div className="flex gap-3">
            <Button onClick={handleGrantConsent} className="flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Allow Location Access
            </Button>
            <Button variant="outline" onClick={handleDenyConsent}>
              Not Now
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Alert className={className}>
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
        <AlertDescription>
          Getting your location for fraud protection...
        </AlertDescription>
      </Alert>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>{error.message}</span>
          {!hasUserDeclined && (
            <Button size="sm" variant="outline" onClick={handleRetryLocation}>
              Retry
            </Button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  if (location) {
    return (
      <Alert className={className}>
        <CheckCircle2 className="h-4 w-4 text-green-500" />
        <AlertDescription className="flex items-center justify-between">
          <span>Location captured for fraud protection</span>
          <Badge variant="secondary" className="text-xs">
            ±{Math.round(location.accuracy)}m accuracy
          </Badge>
        </AlertDescription>
      </Alert>
    );
  }

  if (hasUserDeclined) {
    return (
      <Alert variant="secondary" className={className}>
        <X className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>Location-based fraud detection disabled</span>
          <Button size="sm" variant="outline" onClick={handleRetryLocation}>
            Enable
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}

/**
 * Simplified location status indicator
 */
export function LocationStatus({
  location,
  error,
  className,
}: {
  location: LocationData | null;
  error: LocationError | null;
  className?: string;
}) {
  if (location) {
    return (
      <Badge variant="secondary" className={className}>
        <MapPin className="h-3 w-3 mr-1" />
        Location Active
      </Badge>
    );
  }

  if (error?.code === 1) {
    return (
      <Badge variant="outline" className={className}>
        <X className="h-3 w-3 mr-1" />
        Location Disabled
      </Badge>
    );
  }

  if (error) {
    return (
      <Badge variant="destructive" className={className}>
        <AlertTriangle className="h-3 w-3 mr-1" />
        Location Error
      </Badge>
    );
  }

  return null;
}

/**
 * Location debugging component (dev mode only)
 */
export function LocationDebug({ location }: { location: LocationData | null }) {
  if (!import.meta.env.DEV || !location) return null;

  return (
    <Card className="border-dashed">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Location Debug Info</CardTitle>
      </CardHeader>
      <CardContent className="text-xs font-mono space-y-1">
        <div>Lat: {location.latitude.toFixed(6)}</div>
        <div>Lng: {location.longitude.toFixed(6)}</div>
        <div>Accuracy: ±{Math.round(location.accuracy)}m</div>
        <div>Captured: {new Date(location.timestamp).toLocaleTimeString()}</div>
      </CardContent>
    </Card>
  );
}
