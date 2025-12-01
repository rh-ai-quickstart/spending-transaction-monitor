import { z } from 'zod';
import { AlertRecommendationsResponseSchema } from './recommendation';

/**
 * WebSocket Message Schema
 */
export const WebSocketMessageSchema = z.object({
  type: z.string(),
  user_id: z.string(),
  recommendations: AlertRecommendationsResponseSchema.optional(),
  timestamp: z.string().optional(),
});

/**
 * WebSocket Options Schema
 */
export const UseWebSocketOptionsSchema = z.object({
  userId: z.string(),
});

// Export types
export type WebSocketMessage = z.infer<typeof WebSocketMessageSchema>;

export interface UseWebSocketOptions {
  userId: string;
  onMessage?: (message: WebSocketMessage) => void;
  onRecommendationsReady?: (
    recommendations: z.infer<typeof AlertRecommendationsResponseSchema>,
  ) => void;
}
