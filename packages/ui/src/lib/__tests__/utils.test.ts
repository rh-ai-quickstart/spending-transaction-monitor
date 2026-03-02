/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { cn, formatAmount, formatTime, getStatusColor } from '../utils';

describe('cn', () => {
  it('should merge class names correctly', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });

  it('should handle conditional classes', () => {
    const isTrue = true;
    const isFalse = false;
    expect(cn('base', isTrue && 'conditional', isFalse && 'not-included')).toBe(
      'base conditional',
    );
  });

  it('should handle arrays of classes', () => {
    expect(cn(['class1', 'class2'])).toBe('class1 class2');
  });

  it('should merge tailwind classes correctly', () => {
    expect(cn('p-4', 'p-2')).toBe('p-2');
  });

  it('should handle empty input', () => {
    expect(cn()).toBe('');
  });

  it('should handle undefined and null', () => {
    expect(cn(undefined, 'class1', null, 'class2')).toBe('class1 class2');
  });
});

describe('formatAmount', () => {
  it('should format positive amounts as USD currency', () => {
    expect(formatAmount(100)).toBe('$100.00');
    expect(formatAmount(1234.56)).toBe('$1,234.56');
  });

  it('should format negative amounts as USD currency', () => {
    expect(formatAmount(-100)).toBe('-$100.00');
    expect(formatAmount(-1234.56)).toBe('-$1,234.56');
  });

  it('should format zero correctly', () => {
    expect(formatAmount(0)).toBe('$0.00');
  });

  it('should format decimal amounts correctly', () => {
    expect(formatAmount(99.99)).toBe('$99.99');
    expect(formatAmount(0.01)).toBe('$0.01');
  });

  it('should format large amounts with commas', () => {
    expect(formatAmount(1000000)).toBe('$1,000,000.00');
    expect(formatAmount(1234567.89)).toBe('$1,234,567.89');
  });
});

describe('formatTime', () => {
  beforeEach(() => {
    // Mock the current date to a fixed time for consistent tests
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'));
  });

  it('should return "just now" for times less than a minute ago', () => {
    const thirtySecondsAgo = new Date('2024-01-15T11:59:30Z').toISOString();
    expect(formatTime(thirtySecondsAgo)).toBe('just now');
  });

  it('should format times in minutes for times less than an hour ago', () => {
    const fiveMinutesAgo = new Date('2024-01-15T11:55:00Z').toISOString();
    expect(formatTime(fiveMinutesAgo)).toBe('5 minutes ago');

    const oneMinuteAgo = new Date('2024-01-15T11:59:00Z').toISOString();
    expect(formatTime(oneMinuteAgo)).toBe('1 minute ago');
  });

  it('should format times in hours for times less than a day ago', () => {
    const threeHoursAgo = new Date('2024-01-15T09:00:00Z').toISOString();
    expect(formatTime(threeHoursAgo)).toBe('3 hours ago');

    const oneHourAgo = new Date('2024-01-15T11:00:00Z').toISOString();
    expect(formatTime(oneHourAgo)).toBe('1 hour ago');
  });

  it('should format times in days for times less than a week ago', () => {
    const twoDaysAgo = new Date('2024-01-13T12:00:00Z').toISOString();
    expect(formatTime(twoDaysAgo)).toBe('2 days ago');

    const oneDayAgo = new Date('2024-01-14T12:00:00Z').toISOString();
    expect(formatTime(oneDayAgo)).toBe('1 day ago');
  });

  it('should format as date for times more than a week ago', () => {
    const tenDaysAgo = new Date('2024-01-05T12:00:00Z').toISOString();
    const formatted = formatTime(tenDaysAgo);
    // Just check it's in date format, exact format may vary by locale
    expect(formatted).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
  });

  it('should handle edge cases at boundaries', () => {
    // Exactly 60 minutes ago should show hours
    const sixtyMinutesAgo = new Date('2024-01-15T11:00:00Z').toISOString();
    expect(formatTime(sixtyMinutesAgo)).toBe('1 hour ago');

    // Exactly 24 hours ago should show days
    const twentyFourHoursAgo = new Date('2024-01-14T12:00:00Z').toISOString();
    expect(formatTime(twentyFourHoursAgo)).toBe('1 day ago');
  });
});

describe('getStatusColor', () => {
  it('should return color for PENDING status', () => {
    const color = getStatusColor('PENDING');
    // PENDING lowercased is 'pending' which exists in statusColors
    expect(color).toBeDefined();
    expect(color).toBeTruthy();
  });

  it('should return empty string for APPROVED status (not mapped)', () => {
    const color = getStatusColor('APPROVED');
    // APPROVED lowercased is 'approved' which doesn't exist in statusColors
    expect(color).toBe('');
  });

  it('should return empty string for DECLINED status (not mapped)', () => {
    const color = getStatusColor('DECLINED');
    expect(color).toBe('');
  });

  it('should return empty string for CANCELLED status (not mapped)', () => {
    const color = getStatusColor('CANCELLED');
    expect(color).toBe('');
  });

  it('should return empty string for SETTLED status (not mapped)', () => {
    const color = getStatusColor('SETTLED');
    expect(color).toBe('');
  });

  it('should return empty string for unknown status', () => {
    const color = getStatusColor('unknown' as any);
    expect(color).toBe('');
  });
});
