import { describe, it, expect } from 'vitest';
import {
  statusColors,
  severityColors,
  trendColors,
  chartColors,
  chartBackgrounds,
  chartTokens,
} from '../colors';

describe('statusColors', () => {
  it('should have completed status with correct properties', () => {
    expect(statusColors.completed).toBeDefined();
    expect(statusColors.completed.text).toBeTruthy();
    expect(statusColors.completed.icon).toBeTruthy();
    expect(statusColors.completed.badge).toBeTruthy();
  });

  it('should have pending status with correct properties', () => {
    expect(statusColors.pending).toBeDefined();
    expect(statusColors.pending.text).toBeTruthy();
    expect(statusColors.pending.icon).toBeTruthy();
    expect(statusColors.pending.badge).toBeTruthy();
  });

  it('should have flagged status with correct properties', () => {
    expect(statusColors.flagged).toBeDefined();
    expect(statusColors.flagged.text).toBeTruthy();
    expect(statusColors.flagged.icon).toBeTruthy();
    expect(statusColors.flagged.badge).toBeTruthy();
  });

  it('should have failed status with correct properties', () => {
    expect(statusColors.failed).toBeDefined();
    expect(statusColors.failed.text).toBeTruthy();
    expect(statusColors.failed.icon).toBeTruthy();
    expect(statusColors.failed.badge).toBeTruthy();
  });

  it('should have active status with correct properties', () => {
    expect(statusColors.active).toBeDefined();
    expect(statusColors.active.text).toBeTruthy();
    expect(statusColors.active.icon).toBeTruthy();
    expect(statusColors.active.badge).toBeTruthy();
  });

  it('should have inactive status with correct properties', () => {
    expect(statusColors.inactive).toBeDefined();
    expect(statusColors.inactive.text).toBeTruthy();
    expect(statusColors.inactive.icon).toBeTruthy();
    expect(statusColors.inactive.badge).toBeTruthy();
  });

  it('should have paused status with correct properties', () => {
    expect(statusColors.paused).toBeDefined();
    expect(statusColors.paused.text).toBeTruthy();
    expect(statusColors.paused.icon).toBeTruthy();
    expect(statusColors.paused.badge).toBeTruthy();
  });

  it('should have error status with correct properties', () => {
    expect(statusColors.error).toBeDefined();
    expect(statusColors.error.text).toBeTruthy();
    expect(statusColors.error.icon).toBeTruthy();
    expect(statusColors.error.badge).toBeTruthy();
    expect(statusColors.error.card).toBeTruthy();
  });
});

describe('severityColors', () => {
  it('should have critical severity with correct properties', () => {
    expect(severityColors.critical).toBeDefined();
    expect(severityColors.critical.text).toBeTruthy();
    expect(severityColors.critical.icon).toBeTruthy();
    expect(severityColors.critical.badge).toBeTruthy();
  });

  it('should have high severity with correct properties', () => {
    expect(severityColors.high).toBeDefined();
    expect(severityColors.high.text).toBeTruthy();
    expect(severityColors.high.icon).toBeTruthy();
    expect(severityColors.high.badge).toBeTruthy();
  });

  it('should have medium severity with correct properties', () => {
    expect(severityColors.medium).toBeDefined();
    expect(severityColors.medium.text).toBeTruthy();
    expect(severityColors.medium.icon).toBeTruthy();
    expect(severityColors.medium.badge).toBeTruthy();
  });

  it('should have low severity with correct properties', () => {
    expect(severityColors.low).toBeDefined();
    expect(severityColors.low.text).toBeTruthy();
    expect(severityColors.low.icon).toBeTruthy();
    expect(severityColors.low.badge).toBeTruthy();
  });
});

describe('trendColors', () => {
  it('should have positive trend with correct properties', () => {
    expect(trendColors.positive).toBeDefined();
    expect(trendColors.positive.text).toBeTruthy();
    expect(trendColors.positive.icon).toBeTruthy();
  });

  it('should have negative trend with correct properties', () => {
    expect(trendColors.negative).toBeDefined();
    expect(trendColors.negative.text).toBeTruthy();
    expect(trendColors.negative.icon).toBeTruthy();
  });

  it('should have neutral trend with correct properties', () => {
    expect(trendColors.neutral).toBeDefined();
    expect(trendColors.neutral.text).toBeTruthy();
    expect(trendColors.neutral.icon).toBeTruthy();
  });
});

describe('chartColors', () => {
  it('should have all chart colors defined', () => {
    expect(chartColors.chart1).toBeTruthy();
    expect(chartColors.chart2).toBeTruthy();
    expect(chartColors.chart3).toBeTruthy();
    expect(chartColors.chart4).toBeTruthy();
    expect(chartColors.chart5).toBeTruthy();
  });

  it('should have color classes in correct format', () => {
    expect(chartColors.chart1).toMatch(/^text-chart-\d+$/);
    expect(chartColors.chart2).toMatch(/^text-chart-\d+$/);
  });
});

describe('chartBackgrounds', () => {
  it('should have all chart backgrounds defined', () => {
    expect(chartBackgrounds.chart1).toBeTruthy();
    expect(chartBackgrounds.chart2).toBeTruthy();
    expect(chartBackgrounds.chart3).toBeTruthy();
    expect(chartBackgrounds.chart4).toBeTruthy();
    expect(chartBackgrounds.chart5).toBeTruthy();
  });

  it('should have background classes in correct format', () => {
    expect(chartBackgrounds.chart1).toMatch(/^bg-chart-\d+$/);
    expect(chartBackgrounds.chart2).toMatch(/^bg-chart-\d+$/);
  });
});

describe('chartTokens', () => {
  it('should have all token types defined', () => {
    expect(chartTokens.primary).toBeTruthy();
    expect(chartTokens.secondary).toBeTruthy();
    expect(chartTokens.tertiary).toBeTruthy();
    expect(chartTokens.accent).toBeTruthy();
    expect(chartTokens.warning).toBeTruthy();
  });

  it('should reference CSS custom properties', () => {
    expect(chartTokens.primary).toMatch(/^var\(--chart-\d+\)$/);
    expect(chartTokens.secondary).toMatch(/^var\(--chart-\d+\)$/);
    expect(chartTokens.tertiary).toMatch(/^var\(--chart-\d+\)$/);
    expect(chartTokens.accent).toMatch(/^var\(--chart-\d+\)$/);
    expect(chartTokens.warning).toMatch(/^var\(--chart-\d+\)$/);
  });
});
