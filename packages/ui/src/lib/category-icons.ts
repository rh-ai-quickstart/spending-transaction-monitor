/**
 * Category Icons Mapping
 * Maps TRANSACTION_CATEGORIES to appropriate emoji icons
 */

import { TRANSACTION_CATEGORIES } from '../schemas/transaction';

type TransactionCategory = (typeof TRANSACTION_CATEGORIES)[number];

// Direct mapping of categories to icons
const CATEGORY_ICON_MAP: Record<TransactionCategory, string> = {
  Groceries: '🛒',
  Restaurants: '🍽️',
  Gas: '⛽',
  Entertainment: '🎬',
  Shopping: '🛍️',
  Transportation: '🚗',
  Healthcare: '🏥',
  'Bills & Utilities': '💡',
  'Housing & Rent': '🏠',
  Travel: '✈️',
  Education: '📚',
  Business: '🏢',
  Other: '💰',
} as const;

/**
 * Returns an emoji icon for a transaction category
 * @param category - The transaction category
 * @returns The corresponding emoji icon
 */
export function getCategoryIcon(category?: string): string {
  if (!category) return '💰';

  // Try exact match first
  if (category in CATEGORY_ICON_MAP) {
    return CATEGORY_ICON_MAP[category as TransactionCategory];
  }

  // If no exact match, return default
  return '💰';
}

/**
 * Get all available category icons
 * @returns Object with category-icon pairs
 */
export function getAllCategoryIcons(): Record<TransactionCategory, string> {
  return { ...CATEGORY_ICON_MAP };
}
