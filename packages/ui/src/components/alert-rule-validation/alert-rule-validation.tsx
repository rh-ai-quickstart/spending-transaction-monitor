import { Card } from '../atoms/card/card';
import { Button } from '../atoms/button/button';
import { Badge } from '../atoms/badge/badge';
import { cn } from '../../lib/utils';
import { CheckCircle, AlertTriangle, XCircle, Info, X } from 'lucide-react';

export interface AlertRule {
  name: string;
  description: string;
  alert_type: string;
  amount_threshold?: number;
  merchant_category?: string;
  merchant_name?: string;
  location?: string;
  timeframe?: string;
}

export interface ValidationResult {
  status: 'valid' | 'warning' | 'invalid' | 'error';
  message: string;
  alert_rule?: AlertRule;
  sql_query?: string;
  sql_description?: string;
  similarity_result?: {
    is_similar: boolean;
    similarity_score: number;
    similar_rule?: string;
    reason: string;
  };
  valid_sql?: boolean;
}

export interface AlertRuleValidationProps {
  validationResult: ValidationResult | null;
  onConfirm: () => void;
  onDismiss: () => void;
  isCreating?: boolean;
}

export function AlertRuleValidation({
  validationResult,
  onConfirm,
  onDismiss,
  isCreating = false,
}: AlertRuleValidationProps) {
  if (!validationResult) return null;

  const getStatusIcon = () => {
    switch (validationResult.status) {
      case 'valid':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'invalid':
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Info className="h-5 w-5 text-blue-600" />;
    }
  };

  const getStatusColor = () => {
    switch (validationResult.status) {
      case 'valid':
        return 'border-green-500 bg-green-50 dark:bg-green-950/30';
      case 'warning':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/30';
      case 'invalid':
      case 'error':
        return 'border-red-500 bg-red-50 dark:bg-red-950/30';
      default:
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950/30';
    }
  };

  const getStatusTextColor = () => {
    switch (validationResult.status) {
      case 'valid':
        return 'text-green-900 dark:text-green-100';
      case 'warning':
        return 'text-yellow-900 dark:text-yellow-100';
      case 'invalid':
      case 'error':
        return 'text-red-900 dark:text-red-100';
      default:
        return 'text-blue-900 dark:text-blue-100';
    }
  };

  const canCreate =
    validationResult.status === 'valid' || validationResult.status === 'warning';

  return (
    <div className="mb-8">
      <Card className={cn('border-l-4 p-4', getStatusColor())}>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className="flex-shrink-0">{getStatusIcon()}</div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <p className={cn('font-medium', getStatusTextColor())}>
                  {validationResult.status === 'valid' && 'Rule Validated Successfully'}
                  {validationResult.status === 'warning' && 'Similar Rule Detected'}
                  {validationResult.status === 'invalid' && 'Invalid Rule'}
                  {validationResult.status === 'error' && 'Validation Error'}
                </p>
                <Badge
                  variant="secondary"
                  className={cn(
                    'capitalize',
                    validationResult.status === 'valid' &&
                      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                    validationResult.status === 'warning' &&
                      'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
                    validationResult.status === 'invalid' &&
                      'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
                    validationResult.status === 'error' &&
                      'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
                  )}
                >
                  {validationResult.status}
                </Badge>
              </div>

              <p className={cn('text-sm mb-3', getStatusTextColor())}>
                {validationResult.message}
              </p>

              {/* Similarity Warning */}
              {validationResult.similarity_result?.is_similar && (
                <div className="mb-3 p-3 bg-yellow-100/50 dark:bg-yellow-950/30 rounded-md border border-yellow-200/50 dark:border-yellow-800/30">
                  <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                    Similar Rule Found:
                  </p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300 italic mb-1">
                    "{validationResult.similarity_result.similar_rule}"
                  </p>
                  <p className="text-xs text-yellow-600 dark:text-yellow-400">
                    {validationResult.similarity_result.reason}
                  </p>
                </div>
              )}

              {/* SQL Description */}
              {validationResult.sql_description && (
                <div className="mb-3 p-3 bg-gray-100/50 dark:bg-gray-800/30 rounded-md border border-gray-200/50 dark:border-gray-700/30">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
                    What this rule will do:
                  </p>
                  <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">
                    {validationResult.sql_description}
                  </div>
                </div>
              )}

              {/* SQL Query (for debugging) */}
              {validationResult.sql_query && import.meta.env.MODE === 'development' && (
                <div className="mb-3 p-3 bg-gray-100/50 dark:bg-gray-800/30 rounded-md border border-gray-200/50 dark:border-gray-700/30">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
                    Generated SQL Query:
                  </p>
                  <code className="text-xs text-gray-600 dark:text-gray-400 font-mono block whitespace-pre-wrap">
                    {validationResult.sql_query}
                  </code>
                </div>
              )}

              {/* Action Buttons */}
              {canCreate && (
                <div className="flex gap-2 mt-4">
                  <Button
                    onClick={onConfirm}
                    disabled={isCreating}
                    className={cn(
                      validationResult.status === 'warning'
                        ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                        : 'bg-green-600 hover:bg-green-700 text-white',
                    )}
                  >
                    {isCreating ? 'Creating...' : 'Create Rule'}
                  </Button>
                  <Button variant="outline" onClick={onDismiss} disabled={isCreating}>
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </Card>
    </div>
  );
}
