import { z } from 'zod';
import type { ReactNode } from 'react';

/**
 * Theme Schema
 */
export const ThemeSchema = z.enum(['dark', 'light', 'system']);

/**
 * Time Range Schema
 * Used for filtering data by time periods
 */
export const TimeRangeSchema = z.enum(['7d', '30d', '90d', '1y']);

/**
 * Stat Schema
 * Used for displaying statistics in cards and lists
 */
export const StatSchema = z.object({
  id: z.string(),
  title: z.string(),
  value: z.union([z.string(), z.number()]),
  tone: z.enum(['emerald', 'sky', 'violet']).optional(),
  description: z.string().optional(),
});

// Export types with ReactNode support
export type Theme = z.infer<typeof ThemeSchema>;
export type TimeRange = z.infer<typeof TimeRangeSchema>;
export type Stat = z.infer<typeof StatSchema> & {
  icon?: ReactNode;
  action?: ReactNode;
};

/**
 * Theme Provider Props
 */
export interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

/**
 * Theme Provider State
 */
export interface ThemeProviderState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}
