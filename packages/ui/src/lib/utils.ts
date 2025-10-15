import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { statusColors } from './colors';
import type { Transaction } from '../schemas/transaction';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats a number as USD currency
 */
export function formatAmount(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * Formats a timestamp as relative time (e.g., "2 hours ago", "just now")
 */
export function formatTime(time: string): string {
  const date = new Date(time);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  return date.toLocaleDateString();
}

/**
 * Gets the appropriate CSS class for a transaction status badge
 */
export function getStatusColor(status: Transaction['status']): string {
  return statusColors[status.toLowerCase() as keyof typeof statusColors]?.badge || '';
}
