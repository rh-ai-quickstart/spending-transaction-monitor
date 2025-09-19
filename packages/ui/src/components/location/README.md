# Location Service

## Overview

The location service provides periodic location updates for fraud detection purposes. It automatically captures user location at configurable intervals and sends updates to the backend API.

## Key Features

- **Periodic Updates**: Automatically captures location every 15 minutes (configurable)
- **Retry Logic**: Handles temporary failures with exponential backoff
- **Authentication-Aware**: Only runs when user is authenticated
- **Privacy-Conscious**: Respects user location consent
- **Battery Optimized**: Configurable intervals to balance security and battery life

## Configuration

Set these environment variables in your `.env` file:

```bash
# Location update interval in minutes (default: 15, range: 5-120)
VITE_LOCATION_UPDATE_INTERVAL_MINUTES=15

# Enable/disable periodic updates (default: true)
VITE_ENABLE_PERIODIC_LOCATION_UPDATES=true

# Maximum retry attempts for failed updates (default: 3)
VITE_LOCATION_MAX_RETRY_ATTEMPTS=3

# Delay between retries in milliseconds (default: 5000)
VITE_LOCATION_RETRY_DELAY_MS=5000
```

## Usage

### Basic Setup

The `LocationProvider` is already integrated into the main app. No additional setup is required.

```tsx
// Already configured in main.tsx
<AuthProvider>
  <LocationProvider>
    {/* Your app */}
  </LocationProvider>
</AuthProvider>
```

### Using the Location Context

Access location service status in your components:

```tsx
import { useLocationContext } from '@/components/location/LocationProvider';

function MyComponent() {
  const {
    isActive,
    lastUpdate,
    updateCount,
    lastError,
    nextUpdateIn,
    forceUpdate,
  } = useLocationContext();

  return (
    <div>
      <p>Status: {isActive ? 'Active' : 'Inactive'}</p>
      <p>Updates: {updateCount}</p>
      {lastUpdate && <p>Last: {lastUpdate.toLocaleString()}</p>}
      <button onClick={() => forceUpdate()}>Update Now</button>
    </div>
  );
}
```

### Development Status Component

In development mode, a status component shows location service information:

```tsx
import { LocationStatus } from '@/components/location/LocationProvider';

// Shows location service status in development
<LocationStatus />
```

## API Integration

Location updates are sent to the backend via:

- **Headers**: `X-User-Latitude`, `X-User-Longitude`, `X-User-Location-Accuracy`
- **Endpoint**: `POST /api/users/location`
- **Payload**: Location coordinates and consent status

## Security Considerations

- **Non-User-Configurable**: Update intervals are set via environment variables to prevent security bypasses
- **Consent-Aware**: Respects user location consent settings
- **Authentication Required**: Only works for authenticated users
- **Rate Limited**: Reasonable intervals prevent excessive battery drain
- **Validated Ranges**: Update intervals are constrained to 5-120 minutes

## Testing

Run the location service tests:

```bash
npm test -- usePeriodicLocation
```

## Privacy Notes

- Location data is only captured with user consent
- Updates only occur when user is authenticated
- Location accuracy is included when available
- All updates include consent confirmation

## Browser Requirements

- Modern browsers with Geolocation API support
- HTTPS required for location access (except localhost)
- User must grant location permission
