import { z } from 'zod';

// Transaction type and status enums to match backend
export const TRANSACTION_TYPES = [
  'PURCHASE',
  'REFUND',
  'CASHBACK',
  'FEE',
  'INTEREST',
  'PAYMENT',
] as const;
export const TRANSACTION_STATUSES = [
  'PENDING',
  'APPROVED',
  'DECLINED',
  'CANCELLED',
  'SETTLED',
] as const;

// Common merchant categories
export const TRANSACTION_CATEGORIES = [
  'Groceries',
  'Restaurants',
  'Gas',
  'Entertainment',
  'Shopping',
  'Transportation',
  'Healthcare',
  'Bills & Utilities',
  'Housing & Rent',
  'Travel',
  'Education',
  'Business',
  'Other',
] as const;

// Common account types for demo purposes
export const ACCOUNT_TYPES = [
  'Checking',
  'Savings',
  'Credit Card',
  'Investment',
  'Other',
] as const;

export const TransactionSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  credit_card_num: z.string(),
  amount: z.number().positive(),
  currency: z.string().default('USD'),
  description: z.string(),
  merchant_name: z.string(),
  merchant_category: z.string(),
  transaction_date: z.string(),
  transaction_type: z.enum(TRANSACTION_TYPES).default('PURCHASE'),
  merchant_city: z.string().optional(),
  merchant_state: z.string().optional(),
  merchant_country: z.string().optional(),
  merchant_zipcode: z.string().optional(),
  merchant_latitude: z.number().optional(),
  merchant_longitude: z.number().optional(),
  status: z.enum(TRANSACTION_STATUSES).default('PENDING'),
  authorization_code: z.string().optional(),
  trans_num: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

// Schema for creating a new transaction
export const CreateTransactionSchema = z.object({
  date: z
    .string()
    .min(1, 'Date is required')
    .refine((date) => {
      const parsedDate = new Date(date);
      return !isNaN(parsedDate.getTime());
    }, 'Please enter a valid date')
    .refine((date) => {
      const parsedDate = new Date(date);
      const today = new Date();
      const oneYearAgo = new Date(
        today.getFullYear() - 1,
        today.getMonth(),
        today.getDate(),
      );
      const oneYearFromNow = new Date(
        today.getFullYear() + 1,
        today.getMonth(),
        today.getDate(),
      );
      return parsedDate >= oneYearAgo && parsedDate <= oneYearFromNow;
    }, 'Date must be within the last year and next year'),
  description: z
    .string()
    .min(1, 'Description is required')
    .max(100, 'Description must be less than 100 characters')
    .trim(),
  amount: z
    .number('Amount must be a number')
    .positive('Amount must be greater than 0')
    .max(1000000, 'Amount must be less than $1,000,000')
    .refine((val) => {
      // Check if it has more than 2 decimal places
      return Number(val.toFixed(2)) === val;
    }, 'Amount can have at most 2 decimal places'),
  category: z
    .string()
    .min(1, 'Category is required')
    .refine(
      (val) =>
        TRANSACTION_CATEGORIES.includes(val as (typeof TRANSACTION_CATEGORIES)[number]),
      'Please select a valid category',
    ),
  account: z
    .string()
    .min(1, 'Account is required')
    .refine(
      (val) => ACCOUNT_TYPES.includes(val as (typeof ACCOUNT_TYPES)[number]),
      'Please select a valid account type',
    ),
  type: z.enum(['debit', 'credit']),
  merchant: z.string().max(50, 'Merchant name must be less than 50 characters').trim(),
  merchant_city: z
    .string()
    .max(50, 'City must be less than 50 characters')
    .trim()
    .optional(),
  merchant_state: z
    .string()
    .max(50, 'State must be less than 50 characters')
    .trim()
    .optional(),
  merchant_country: z
    .string()
    .max(50, 'Country must be less than 50 characters')
    .trim()
    .optional(),
  tags: z.array(z.string()),
  notes: z.string().max(500, 'Notes must be less than 500 characters').trim(),
});

export const TransactionStatsSchema = z.object({
  totalTransactions: z.number(),
  totalVolume: z.number(),
  activeAlerts: z.number(),
  avgProcessingTime: z.number(),
  previousPeriod: z.object({
    totalTransactions: z.number(),
    totalVolume: z.number(),
    activeAlerts: z.number(),
    avgProcessingTime: z.number(),
  }),
});

export const AlertRuleSchema = z.object({
  id: z.string(),
  rule: z.string(),
  status: z.enum(['active', 'inactive', 'paused']),
  triggered: z.number(),
  last_triggered: z.string(),
  created_at: z.string(),
});

export const AlertSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  timestamp: z.string(),
  transaction_id: z.string().optional(),
  resolved: z.boolean().default(false),
});

// API Response Schemas
export const ApiTransactionResponseSchema = z.object({
  id: z.string(),
  amount: z.number(),
  merchant_name: z.string(),
  status: z.string(),
  transaction_date: z.string(),
  transaction_type: z.string(),
  currency: z.string(),
  merchant_category: z.string(),
  description: z.string(),
  user_id: z.string(),
  trans_num: z.string(),
  // Location fields (optional)
  merchant_city: z.string().nullable().optional(),
  merchant_state: z.string().nullable().optional(),
  merchant_country: z.string().nullable().optional(),
  merchant_zipcode: z.string().nullable().optional(),
  merchant_latitude: z.number().nullable().optional(),
  merchant_longitude: z.number().nullable().optional(),
  authorization_code: z.string().nullable().optional(),
});

export const ApiNotificationResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  message: z.string(),
  notification_method: z.string(),
  status: z.string(),
  created_at: z.string(),
  read: z.boolean(),
  transaction_id: z.string().optional(),
  read_at: z.string().nullable().optional(),
});

export const AlertRuleDataSchema = z.object({
  name: z.string(),
  description: z.string(),
  alert_type: z.string(),
  amount_threshold: z.number().optional(),
  merchant_category: z.string().optional(),
  merchant_name: z.string().optional(),
  location: z.string().optional(),
  timeframe: z.string().optional(),
});

export const SimilarityResultSchema = z.object({
  is_similar: z.boolean(),
  similarity_score: z.number(),
  similar_rule: z.string().optional(),
  reason: z.string(),
});

export const AlertTriggerHistorySchema = z.object({
  id: z.string(),
  title: z.string(),
  message: z.string(),
  notification_method: z.string(),
  status: z.string(),
  user_id: z.string(),
  alert_rule_id: z.string(),
  transaction_id: z.string().optional(),
  sent_at: z.string().nullable(),
  delivered_at: z.string().nullable(),
  read_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Transaction = z.infer<typeof TransactionSchema>;
export type CreateTransaction = z.infer<typeof CreateTransactionSchema>;
export type TransactionStats = z.infer<typeof TransactionStatsSchema>;
export type AlertRule = z.infer<typeof AlertRuleSchema>;
export type Alert = z.infer<typeof AlertSchema>;
export type ApiTransactionResponse = z.infer<typeof ApiTransactionResponseSchema>;
export type ApiNotificationResponse = z.infer<typeof ApiNotificationResponseSchema>;
export type AlertRuleData = z.infer<typeof AlertRuleDataSchema>;
export type SimilarityResult = z.infer<typeof SimilarityResultSchema>;
export type AlertTriggerHistory = z.infer<typeof AlertTriggerHistorySchema>;
