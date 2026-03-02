import { describe, it, expect } from 'vitest';
import { categoryIcons, priorityColors } from '../recommendation-constants';

describe('recommendation-constants', () => {
  describe('categoryIcons', () => {
    it('should define icons for each category', () => {
      expect(categoryIcons).toBeDefined();
      expect(categoryIcons.fraud_protection).toBeDefined();
      expect(categoryIcons.spending_threshold).toBeDefined();
      expect(categoryIcons.location_based).toBeDefined();
      expect(categoryIcons.merchant_monitoring).toBeDefined();
      expect(categoryIcons.subscription_monitoring).toBeDefined();
    });

    it('should have all required category types', () => {
      const categories = Object.keys(categoryIcons);
      expect(categories).toContain('fraud_protection');
      expect(categories).toContain('spending_threshold');
      expect(categories).toContain('location_based');
      expect(categories).toContain('merchant_monitoring');
      expect(categories).toContain('subscription_monitoring');
    });
  });

  describe('priorityColors', () => {
    it('should define colors for each priority level', () => {
      expect(priorityColors).toBeDefined();
      expect(priorityColors.high).toBeTruthy();
      expect(priorityColors.medium).toBeTruthy();
      expect(priorityColors.low).toBeTruthy();
    });

    it('should have color strings', () => {
      expect(typeof priorityColors.high).toBe('string');
      expect(typeof priorityColors.medium).toBe('string');
      expect(typeof priorityColors.low).toBe('string');
    });
  });
});
