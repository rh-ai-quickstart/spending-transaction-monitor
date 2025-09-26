import { useState } from 'react';
import { Card } from '../atoms/card/card';
import { Button } from '../atoms/button/button';
import { Badge } from '../atoms/badge/badge';
import {
  Lightbulb,
  ChevronRight,
  Shield,
  CreditCard,
  MapPin,
  TrendingUp,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface AlertRecommendation {
  title: string;
  description: string;
  natural_language_query: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
  reasoning: string;
}

interface AlertRecommendationsResponse {
  user_id: string;
  recommendation_type: 'new_user' | 'transaction_based';
  recommendations: AlertRecommendation[];
  generated_at: string;
}

interface AlertRecommendationsProps {
  recommendations: AlertRecommendationsResponse | null;
  isLoading: boolean;
  onCreateRule: (recommendation: AlertRecommendation) => Promise<void>;
}

const categoryIcons = {
  fraud_protection: Shield,
  spending_threshold: CreditCard,
  location_based: MapPin,
  merchant_monitoring: TrendingUp,
  subscription_monitoring: TrendingUp,
} as const;

const priorityColors = {
  high: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800',
  medium:
    'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-950 dark:text-yellow-300 dark:border-yellow-800',
  low: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800',
};

export function AlertRecommendations({
  recommendations,
  isLoading,
  onCreateRule,
}: AlertRecommendationsProps) {
  const [expandedCard, setExpandedCard] = useState<number | null>(null);
  const [createdRules, setCreatedRules] = useState<Set<string>>(new Set());
  const [creatingIndex, setCreatingIndex] = useState<number | null>(null);

  const handleCreateRule = async (
    index: number,
    recommendation: AlertRecommendation,
  ) => {
    try {
      setCreatingIndex(index);
      await onCreateRule(recommendation);

      // Mark this rule as created using the natural language query as stable identifier
      setCreatedRules((prev) =>
        new Set(prev).add(recommendation.natural_language_query),
      );
    } catch (error) {
      console.error('Failed to create rule:', error);
    } finally {
      setCreatingIndex(null);
    }
  };

  const toggleExpanded = (index: number) => {
    setExpandedCard(expandedCard === index ? null : index);
  };

  if (isLoading) {
    return (
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Lightbulb className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Recommended Alerts</h2>
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
      <div className="flex items-center gap-3 mb-4">
        <Lightbulb className="h-5 w-5 text-primary" />
        <div>
          <h2 className="text-xl font-semibold text-foreground">Recommended Alerts</h2>
          <p className="text-sm text-muted-foreground">
            {recommendation_type === 'new_user'
              ? 'Get started with these essential alerts based on your profile'
              : 'Personalized alerts based on your spending patterns'}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {recs.slice(0, 6).map((rec, index) => {
          const IconComponent =
            categoryIcons[rec.category as keyof typeof categoryIcons] || AlertTriangle;
          const isExpanded = expandedCard === index;
          const isCreated = createdRules.has(rec.natural_language_query);
          const isCreatingThis = creatingIndex === index;

          // Don't render created rules
          if (isCreated) {
            return null;
          }

          return (
            <Card
              key={rec.natural_language_query}
              className={cn(
                'border-l-4 p-4',
                rec.priority === 'high'
                  ? 'border-l-red-500'
                  : rec.priority === 'medium'
                    ? 'border-l-yellow-500'
                    : 'border-l-blue-500',
                isCreated &&
                  'bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <IconComponent className="h-4 w-4 text-muted-foreground" />
                    <p className="font-medium text-foreground">{rec.title}</p>
                    <Badge
                      variant="outline"
                      className={cn('text-xs', priorityColors[rec.priority])}
                    >
                      {rec.priority}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                    <span>{rec.description}</span>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 space-y-3">
                      <div className="p-3 bg-muted/50 rounded-md">
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          Alert Rule:
                        </p>
                        <p className="text-sm font-mono italic">
                          "{rec.natural_language_query}"
                        </p>
                      </div>
                      <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-md">
                        <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
                          Why this helps:
                        </p>
                        <p className="text-sm text-blue-700 dark:text-blue-300">
                          {rec.reasoning}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCreateRule(index, rec)}
                    disabled={isCreatingThis}
                  >
                    {isCreatingThis ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <CreditCard className="h-4 w-4 mr-1" />
                    )}
                    {isCreatingThis ? 'Creating...' : 'Add Alert'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleExpanded(index)}
                    className="p-1"
                  >
                    <ChevronRight
                      className={cn(
                        'h-4 w-4 transition-transform',
                        isExpanded && 'rotate-90',
                      )}
                    />
                  </Button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {recs.length > 4 && (
        <div className="mt-3 text-center">
          <Button variant="ghost" size="sm" className="text-xs">
            View {recs.length - 4} more recommendations
          </Button>
        </div>
      )}
    </div>
  );
}
