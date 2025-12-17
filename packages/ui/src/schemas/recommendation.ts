import { z } from 'zod';

export const AlertRecommendationSchema = z.object({
  title: z.string(),
  description: z.string(),
  natural_language_query: z.string(),
  category: z.string(),
  priority: z.enum(['high', 'medium', 'low']),
  reasoning: z.string(),
});

export const AlertRecommendationsResponseSchema = z.object({
  user_id: z.string(),
  recommendation_type: z.enum([
    'new_user',
    'transaction_based',
    'placeholder',
    'ml_default',
    'ml_collaborative_filtering',
    'default',
  ]),
  recommendations: z.array(AlertRecommendationSchema),
  generated_at: z.string(),
  is_placeholder: z.boolean().optional(),
  message: z.string().optional(),
});

export const RecommendationCategoriesResponseSchema = z.object({
  categories: z.record(z.string(), z.array(z.string())),
});

export const RecommendationCreateRequestSchema = z.object({
  title: z.string(),
  description: z.string(),
  natural_language_query: z.string(),
  category: z.string(),
  priority: z.string(),
  reasoning: z.string(),
});

export type AlertRecommendation = z.infer<typeof AlertRecommendationSchema>;
export type AlertRecommendationsResponse = z.infer<
  typeof AlertRecommendationsResponseSchema
>;
export type RecommendationCategoriesResponse = z.infer<
  typeof RecommendationCategoriesResponseSchema
>;
export type RecommendationCreateRequest = z.infer<
  typeof RecommendationCreateRequestSchema
>;
