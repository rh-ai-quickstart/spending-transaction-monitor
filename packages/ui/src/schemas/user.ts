import { z } from 'zod';

/**
 * API User Response Schema
 * Represents the full user data from the backend API
 */
export const ApiUserResponseSchema = z.object({
  id: z.string(),
  first_name: z.string(),
  last_name: z.string(),
  email: z.string().email(),
  phone_number: z.string(),
  address: z.string(),
  city: z.string(),
  state: z.string(),
  zip: z.string(),
  created_at: z.string(),
});

/**
 * API Credit Card Response Schema
 */
export const ApiCreditCardResponseSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  card_number: z.string(),
  card_type: z.string(),
  expiry_date: z.string(),
  credit_limit: z.number(),
  current_balance: z.number(),
  available_credit: z.number(),
});

/**
 * API Alert Rule Response Schema
 */
export const ApiAlertRuleResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  natural_language_query: z.string(),
  sql_query: z.string(),
  alert_type: z.string(),
  is_active: z.boolean(),
  trigger_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  last_triggered: z.string().optional(),
});

/**
 * Current User Schema
 * Simplified user interface for session management
 */
export const CurrentUserSchema = z.object({
  id: z.string(),
  firstName: z.string(),
  lastName: z.string(),
  email: z.string().email(),
  phone: z.string().optional(),
  fullName: z.string(),
});

/**
 * Use Current User Result Schema
 * Return type for the useCurrentUser hook
 */
export const UseCurrentUserResultSchema = z.object({
  user: CurrentUserSchema.nullable(),
  isLoading: z.boolean(),
  error: z.string().nullable(),
});

// Export types
export type ApiUserResponse = z.infer<typeof ApiUserResponseSchema>;
export type ApiCreditCardResponse = z.infer<typeof ApiCreditCardResponseSchema>;
export type ApiAlertRuleResponse = z.infer<typeof ApiAlertRuleResponseSchema>;
export type CurrentUser = z.infer<typeof CurrentUserSchema>;
export type UseCurrentUserResult = z.infer<typeof UseCurrentUserResultSchema> & {
  refreshUser: () => Promise<void>;
  logout: () => void;
};
