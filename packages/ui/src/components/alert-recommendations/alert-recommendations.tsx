import { useState, useEffect } from 'react';
import { Lightbulb, WifiOff, Loader2 } from 'lucide-react';
import { Card } from '../atoms/card/card';
import { Button } from '../atoms/button/button';
import { RecommendationCard } from './recommendation-card';
import { useRecommendations } from '../../hooks/recommendations';
import type { AlertRecommendation } from '../../schemas/recommendation';
import { useWebSocket } from '../../hooks/useWebSocket';
import { cn } from '../../lib/utils';

export function AlertRecommendations() {
  const {
    data: recommendations,
    isLoading,
    removeRecommendation,
    refetch,
  } = useRecommendations();

  const [isGeneratingPersonalized, setIsGeneratingPersonalized] = useState(false);
  const [showAllRecommendations, setShowAllRecommendations] = useState(false);

  // WebSocket integration for real-time recommendation updates
  const currentUserId = recommendations?.user_id || 'u-011';
  const { isConnected } = useWebSocket({
    userId: currentUserId,
    onRecommendationsReady: (newRecommendations) => {
      console.log('Received new recommendations via WebSocket:', newRecommendations);
      setIsGeneratingPersonalized(false);
      // Refetch recommendations to get the latest data from the server
      refetch();
    },
  });

  // Check if we're showing placeholder recommendations
  const isPlaceholder =
    recommendations?.is_placeholder ||
    recommendations?.recommendation_type === 'placeholder';

  // Manage generating state based on recommendation type
  useEffect(() => {
    if (recommendations) {
      if (isPlaceholder) {
        // Show generating indicator for placeholder recommendations
        setIsGeneratingPersonalized(true);
      } else {
        // Hide generating indicator for real recommendations
        setIsGeneratingPersonalized(false);
      }
    }
  }, [recommendations, isPlaceholder]);

  if (isLoading) {
    return (
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Lightbulb className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Recommended Rules</h2>
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-4">
              <div className="animate-pulse">
                <div className="h-5 bg-muted rounded w-3/4 mb-2" />
                <div className="h-4 bg-muted rounded w-1/2" />
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!recommendations || recommendations.recommendations.length === 0) {
    return null; // Don't show anything if no recommendations
  }

  const { recommendation_type, recommendations: recs } = recommendations;

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Lightbulb className="h-5 w-5 text-primary" />
          <div>
            <h2 className="text-xl font-semibold text-foreground">Recommended Rules</h2>
            <p className="text-sm text-muted-foreground">
              {recommendation_type === 'new_user'
                ? 'Get started with these essential rules based on your profile'
                : recommendation_type === 'placeholder'
                  ? 'Showing general recommendations while we analyze your spending patterns...'
                  : 'Personalized rules based on your spending patterns'}
            </p>
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex items-center gap-2">
          {/* WebSocket connection status */}
          <div className="flex items-center gap-0.5 text-xs">
            {isConnected ? (
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
            ) : (
              <WifiOff className="h-3 w-3 text-red-500" />
            )}
            <span
              className={cn('text-xs', isConnected ? 'text-green-600' : 'text-red-600')}
            >
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>

          {/* Generating personalized recommendations indicator */}
          {isGeneratingPersonalized && (
            <div className="flex items-center gap-1 text-xs text-blue-600">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Generating personalized recommendations...</span>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3 transition-all duration-300">
        {(showAllRecommendations ? recs : recs.slice(0, 4)).map(
          (rec: AlertRecommendation) => (
            <RecommendationCard
              key={rec.natural_language_query}
              recommendation={rec}
              onCreated={() => removeRecommendation(rec.natural_language_query)}
            />
          ),
        )}
      </div>

      {recs.length > 4 && (
        <div className="mt-3 text-center">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs hover:bg-muted/50 transition-colors"
            onClick={() => setShowAllRecommendations(!showAllRecommendations)}
          >
            {showAllRecommendations
              ? 'Show Less'
              : `View ${recs.length - 4} more recommendations`}
          </Button>
        </div>
      )}
    </div>
  );
}
