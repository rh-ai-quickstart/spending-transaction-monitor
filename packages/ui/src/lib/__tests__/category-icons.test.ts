import { describe, it, expect } from 'vitest';
import { getCategoryIcon, getAllCategoryIcons } from '../category-icons';

describe('getCategoryIcon', () => {
  it('should return shopping icon for Shopping category', () => {
    const icon = getCategoryIcon('Shopping');
    expect(icon).toBe('🛍️');
  });

  it('should return groceries icon for Groceries category', () => {
    const icon = getCategoryIcon('Groceries');
    expect(icon).toBe('🛒');
  });

  it('should return restaurants icon for Restaurants category', () => {
    const icon = getCategoryIcon('Restaurants');
    expect(icon).toBe('🍽️');
  });

  it('should return transportation icon for Transportation category', () => {
    const icon = getCategoryIcon('Transportation');
    expect(icon).toBe('🚗');
  });

  it('should return housing icon for Housing & Rent category', () => {
    const icon = getCategoryIcon('Housing & Rent');
    expect(icon).toBe('🏠');
  });

  it('should return healthcare icon for Healthcare category', () => {
    const icon = getCategoryIcon('Healthcare');
    expect(icon).toBe('🏥');
  });

  it('should return entertainment icon for Entertainment category', () => {
    const icon = getCategoryIcon('Entertainment');
    expect(icon).toBe('🎬');
  });

  it('should return gas icon for Gas category', () => {
    const icon = getCategoryIcon('Gas');
    expect(icon).toBe('⛽');
  });

  it('should return bills icon for Bills & Utilities category', () => {
    const icon = getCategoryIcon('Bills & Utilities');
    expect(icon).toBe('💡');
  });

  it('should return travel icon for Travel category', () => {
    const icon = getCategoryIcon('Travel');
    expect(icon).toBe('✈️');
  });

  it('should return education icon for Education category', () => {
    const icon = getCategoryIcon('Education');
    expect(icon).toBe('📚');
  });

  it('should return business icon for Business category', () => {
    const icon = getCategoryIcon('Business');
    expect(icon).toBe('🏢');
  });

  it('should return other icon for Other category', () => {
    const icon = getCategoryIcon('Other');
    expect(icon).toBe('💰');
  });

  it('should return default icon for unknown category', () => {
    const icon = getCategoryIcon('Unknown Category');
    expect(icon).toBe('💰');
  });

  it('should return default icon for empty string', () => {
    const icon = getCategoryIcon('');
    expect(icon).toBe('💰');
  });

  it('should return default icon for undefined', () => {
    const icon = getCategoryIcon(undefined);
    expect(icon).toBe('💰');
  });
});

describe('getAllCategoryIcons', () => {
  it('should return all category icons', () => {
    const icons = getAllCategoryIcons();
    expect(Object.keys(icons)).toHaveLength(13);
  });

  it('should include all expected categories', () => {
    const icons = getAllCategoryIcons();
    expect(icons.Shopping).toBe('🛍️');
    expect(icons.Groceries).toBe('🛒');
    expect(icons.Restaurants).toBe('🍽️');
    expect(icons.Transportation).toBe('🚗');
    expect(icons['Housing & Rent']).toBe('🏠');
    expect(icons.Healthcare).toBe('🏥');
    expect(icons.Entertainment).toBe('🎬');
    expect(icons.Gas).toBe('⛽');
    expect(icons['Bills & Utilities']).toBe('💡');
    expect(icons.Travel).toBe('✈️');
    expect(icons.Education).toBe('📚');
    expect(icons.Business).toBe('🏢');
    expect(icons.Other).toBe('💰');
  });
});
