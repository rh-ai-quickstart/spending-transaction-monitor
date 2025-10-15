import { useState } from 'react';
import { Card } from '../atoms/card/card';
import { Button } from '../atoms/button/button';
import { Badge } from '../atoms/badge/badge';
import { ChevronDown, ChevronUp, Plus, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { priorityColors } from '../../lib/recommendation-constants';
import { useCreateRuleFromRecommendation } from '../../hooks/recommendations';
import type { AlertRecommendation } from '../../schemas/recommendation';

interface RecommendationCardProps {
  recommendation: AlertRecommendation;
  onCreated?: () => void;
}

export function RecommendationCard({
  recommendation,
  onCreated,
}: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCreated, setIsCreated] = useState(false);
  const createRuleMutation = useCreateRuleFromRecommendation();

  // Category icon removed per design update

  const handleCreateRule = async () => {
    try {
      await createRuleMutation.mutateAsync(recommendation);
      setIsCreated(true);
      onCreated?.();
    } catch (error) {
      console.error('Failed to create rule:', error);
    }
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  // Don't render if already created
  if (isCreated) {
    return null;
  }

  return (
    <Card
      className={cn(
        'border-l-4 p-4',
        recommendation.priority === 'high'
          ? 'border-l-red-500'
          : recommendation.priority === 'medium'
            ? 'border-l-yellow-500'
            : 'border-l-blue-500',
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleExpanded}
              className="flex-shrink-0"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
            <p className="font-medium text-foreground">{recommendation.title}</p>
            <Badge
              variant="outline"
              className={cn('text-xs', priorityColors[recommendation.priority])}
            >
              {recommendation.priority}
            </Badge>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{recommendation.description}</span>
          </div>

          {/* Expanded content moved below the header */}
        </div>
        <div className="flex items-center">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCreateRule}
            disabled={createRuleMutation.isPending}
          >
            {createRuleMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Plus className="h-4 w-4 mr-1" />
            )}
            {createRuleMutation.isPending ? 'Creating...' : 'Add Rule'}
          </Button>
        </div>
      </div>
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="space-y-3">
            <div className="p-3 bg-muted/50 rounded-md">
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Alert Rule:
              </p>
              <p className="text-sm font-mono italic">
                "{recommendation.natural_language_query}"
              </p>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-md">
              <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
                Why this helps:
              </p>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {recommendation.reasoning}
              </p>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
