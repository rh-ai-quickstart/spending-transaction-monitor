/**
 * Semantic color mappings for consistent theming across the application
 */

export const statusColors = {
  completed: {
    text: 'text-success',
    icon: 'text-success',
    badge: 'bg-success-muted text-success-muted-foreground',
  },
  pending: {
    text: 'text-warning',
    icon: 'text-warning',
    badge: 'bg-warning-muted text-warning-muted-foreground',
  },
  flagged: {
    text: 'text-error',
    icon: 'text-error',
    badge: 'bg-error-muted text-error-muted-foreground',
  },
  failed: {
    text: 'text-muted-foreground',
    icon: 'text-muted-foreground',
    badge: 'bg-muted text-muted-foreground',
  },
  active: {
    text: 'text-success',
    icon: 'text-success',
    badge: 'bg-success-muted text-success-muted-foreground',
  },
  inactive: {
    text: 'text-orange-600',
    icon: 'text-orange-600',
    badge: 'bg-orange-100 text-orange-800',
  },
  paused: {
    text: 'text-warning',
    icon: 'text-warning',
    badge: 'bg-warning-muted text-warning-muted-foreground',
  },
  error: {
    text: 'text-red-600 dark:text-red-400',
    icon: 'text-red-600 dark:text-red-400',
    badge:
      'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900',
    card: 'border-l-red-500 bg-red-50/50 dark:bg-red-950/50',
  },
} as const;

export const severityColors = {
  critical: {
    text: 'text-error',
    icon: 'text-error',
    badge: 'bg-error-muted text-error-muted-foreground',
  },
  high: {
    text: 'text-error',
    icon: 'text-error',
    badge: 'bg-error-muted text-error-muted-foreground',
  },
  medium: {
    text: 'text-warning',
    icon: 'text-warning',
    badge: 'bg-warning-muted text-warning-muted-foreground',
  },
  low: {
    text: 'text-info',
    icon: 'text-info',
    badge: 'bg-info-muted text-info-muted-foreground',
  },
} as const;

export const trendColors = {
  positive: {
    text: 'text-success',
    icon: 'text-success',
  },
  negative: {
    text: 'text-error',
    icon: 'text-error',
  },
  neutral: {
    text: 'text-muted-foreground',
    icon: 'text-muted-foreground',
  },
} as const;

export const chartColors = {
  chart1: 'text-chart-1', // Orange/Amber
  chart2: 'text-chart-2', // Blue
  chart3: 'text-chart-3', // Dark Blue
  chart4: 'text-chart-4', // Yellow/Green
  chart5: 'text-chart-5', // Orange/Red
} as const;

export const chartBackgrounds = {
  chart1: 'bg-chart-1',
  chart2: 'bg-chart-2',
  chart3: 'bg-chart-3',
  chart4: 'bg-chart-4',
  chart5: 'bg-chart-5',
} as const;

/**
 * Chart color CSS variables for use in charts and visualizations:
 * - --chart-1: Orange/Amber for primary data series
 * - --chart-2: Blue for secondary data series
 * - --chart-3: Dark Blue for tertiary data series
 * - --chart-4: Yellow/Green for accent data
 * - --chart-5: Orange/Red for warning/alert data
 */
export const chartTokens = {
  primary: 'var(--chart-1)',
  secondary: 'var(--chart-2)',
  tertiary: 'var(--chart-3)',
  accent: 'var(--chart-4)',
  warning: 'var(--chart-5)',
} as const;

export type StatusType = keyof typeof statusColors;
export type SeverityType = keyof typeof severityColors;
export type TrendType = keyof typeof trendColors;
export type ChartColor = keyof typeof chartColors;
