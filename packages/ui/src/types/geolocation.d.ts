// Geolocation API type definitions for better TypeScript support
declare global {
  interface Navigator {
    geolocation: Geolocation;
  }

  interface Geolocation {
    getCurrentPosition(
      successCallback: PositionCallback,
      errorCallback?: PositionErrorCallback,
      options?: PositionOptions,
    ): void;
    watchPosition(
      successCallback: PositionCallback,
      errorCallback?: PositionErrorCallback,
      options?: PositionOptions,
    ): number;
    clearWatch(watchId: number): void;
  }

  interface PositionCallback {
    (position: GeolocationPosition): void;
  }

  interface PositionErrorCallback {
    (error: GeolocationPositionError): void;
  }

  interface PositionOptions {
    enableHighAccuracy?: boolean;
    timeout?: number;
    maximumAge?: number;
  }

  interface GeolocationPosition {
    coords: GeolocationCoordinates;
    timestamp: number;
  }

  interface GeolocationCoordinates {
    latitude: number;
    longitude: number;
    altitude?: number | null;
    accuracy: number;
    altitudeAccuracy?: number | null;
    heading?: number | null;
    speed?: number | null;
  }

  interface GeolocationPositionError {
    code: number;
    message: string;
    readonly PERMISSION_DENIED: 1;
    readonly POSITION_UNAVAILABLE: 2;
    readonly TIMEOUT: 3;
  }
}

export {};
