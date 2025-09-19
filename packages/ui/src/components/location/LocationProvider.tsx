/**
 * LocationProvider component that manages periodic location updates
 * This component should be placed high in the component tree to ensure
 * location updates continue running throughout the app lifecycle
 */
/* eslint-disable react-refresh/only-export-components */

import React, { createContext, useContext } from 'react';
import { usePeriodicLocation } from '@/hooks/usePeriodicLocation';

interface LocationContextValue {
  isActive: boolean;
  lastUpdate: Date | null;
  updateCount: number;
  lastError: string | null;
  nextUpdateIn: number;
  start: () => void;
  stop: (manual?: boolean) => void;
  forceUpdate: () => Promise<void>;
}

const LocationContext = createContext<LocationContextValue | null>(null);

export function useLocationContext(): LocationContextValue {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error('useLocationContext must be used within a LocationProvider');
  }
  return context;
}

interface LocationProviderProps {
  children: React.ReactNode;
}

export function LocationProvider({ children }: LocationProviderProps) {
  const periodicLocation = usePeriodicLocation();

  return (
    <LocationContext.Provider value={periodicLocation}>
      {children}
    </LocationContext.Provider>
  );
}

