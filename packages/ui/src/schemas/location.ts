import { z } from 'zod';

/**
 * Location data schema - consolidated from LocationData and UserLocation
 * Represents geographic coordinates with accuracy information
 */
export const LocationSchema = z.object({
  latitude: z.number(),
  longitude: z.number(),
  accuracy: z.number(),
  timestamp: z.number().optional(),
});

/**
 * Location error schema
 */
export const LocationErrorSchema = z.object({
  code: z.number(),
  message: z.string(),
});

/**
 * Location result hook return type schema
 */
export const UseLocationResultSchema = z.object({
  location: LocationSchema.nullable(),
  error: LocationErrorSchema.nullable(),
  isLoading: z.boolean(),
  isSupported: z.boolean(),
});

// Export types
export type Location = z.infer<typeof LocationSchema>;
export type LocationError = z.infer<typeof LocationErrorSchema>;
export type UseLocationResult = z.infer<typeof UseLocationResultSchema> & {
  requestLocation: () => void;
  clearLocation: () => void;
};

/**
 * Helper function to create location headers for API requests
 */
export function createLocationHeaders(
  location: Location | null,
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
