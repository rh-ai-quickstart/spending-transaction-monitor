import { z } from 'zod';

/**
 * API Client Configuration Schema
 */
export const ApiClientConfigSchema = z.object({
  baseUrl: z.string().optional(),
  timeout: z.number().optional(),
  includeLocation: z.boolean().optional(),
  headers: z.record(z.string(), z.string()).optional(),
});

/**
 * API Response Schema
 * Generic schema for API responses
 */
export const ApiResponseSchema = z.object({
  status: z.number(),
  statusText: z.string(),
});

/**
 * API Notification Response Schema
 */
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

/**
 * Alert Rule Data Schema
 * Used for creating/validating alert rules
 */
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

/**
 * Similarity Result Schema
 * Used for checking if alert rules are similar to existing ones
 */
export const SimilarityResultSchema = z.object({
  is_similar: z.boolean(),
  similarity_score: z.number(),
  similar_rule: z.string().optional(),
  reason: z.string(),
});

/**
 * Validation Result Schema
 * Used for alert rule validation responses
 */
export const ValidationResultSchema = z.object({
  status: z.enum(['valid', 'warning', 'invalid', 'error']),
  message: z.string(),
  alert_rule: AlertRuleDataSchema.optional(),
  sql_query: z.string().optional(),
  sql_description: z.string().optional(),
  similarity_result: SimilarityResultSchema.optional(),
  valid_sql: z.boolean().optional(),
});

// Export types
export type ApiClientConfig = z.infer<typeof ApiClientConfigSchema>;
export type ApiResponse<T = unknown> = z.infer<typeof ApiResponseSchema> & {
  data: T;
  headers: Headers;
};
export type ApiNotificationResponse = z.infer<typeof ApiNotificationResponseSchema>;
export type AlertRuleData = z.infer<typeof AlertRuleDataSchema>;
export type SimilarityResult = z.infer<typeof SimilarityResultSchema>;
export type ValidationResult = z.infer<typeof ValidationResultSchema>;
