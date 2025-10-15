/**
 * Expandable Alert Rule Card Component
 * Shows alert rule with expandable trigger history
 */

import { useState } from 'react';
import { Badge } from '../atoms/badge/badge';
import { Button } from '../atoms/button/button';
import { Card } from '../atoms/card/card';
import { cn } from '../../lib/utils';
import { statusColors } from '../../lib/colors';
import { useAlertRuleHistory } from '../../hooks/alert';
import {
  ChevronDown,
  ChevronUp,
  Pause,
  Play,
  Trash2,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import type { AlertRule } from '../../schemas/transaction';

export interface AlertRuleCardProps {
  rule: AlertRule;
  onToggle: (id: string) => void;
  onDelete: (id: string, name: string) => void;
  isToggling?: boolean;
  isDeleting?: boolean;
}

function getNotificationStatusIcon(status: string) {
  switch (status.toLowerCase()) {
    case 'sent':
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-600" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-600" />;
    default:
      return <AlertTriangle className="h-4 w-4 text-gray-600" />;
  }
}

function formatTriggerDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function AlertRuleCard({
  rule,
  onToggle,
  onDelete,
  isToggling = false,
  isDeleting = false,
}: AlertRuleCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { data: alertHistory, isLoading: isLoadingHistory } = useAlertRuleHistory(
    isExpanded ? rule.id : '',
  );

  return (
    <Card
      className={cn(
        'border-l-4 p-4 transition-all duration-200',
        rule.status === 'active' ? 'border-l-primary' : 'border-l-muted',
      )}
    >
      {/* Main Card Content */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          {/* Expand/Collapse Button - Always visible on left */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Hide alert history' : 'Show alert history'}
            className="flex-shrink-0"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <p className="font-medium text-foreground">{rule.rule}</p>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>Triggered {rule.triggered} times</span>
              <span>•</span>
              <span>Last: {rule.last_triggered}</span>
              <span>•</span>
              <span>
                Alert history:{' '}
                {rule.triggered > 0 ? `${rule.triggered} alerts` : 'None'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant="secondary"
            className={cn(
              'capitalize',
              statusColors[rule.status as keyof typeof statusColors]?.badge ||
                'bg-muted text-muted-foreground',
            )}
          >
            {rule.status}
          </Badge>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => onToggle(rule.id)}
            disabled={isToggling}
            title={rule.status === 'active' ? 'Pause alert rule' : 'Resume alert rule'}
          >
            {rule.status === 'active' ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4 text-green-600" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(rule.id, rule.rule)}
            disabled={isDeleting}
          >
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </div>

      {/* Expandable Alert History */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <h4 className="font-medium text-foreground">Alert History</h4>
          </div>

          {isLoadingHistory ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
              <span className="ml-2 text-sm text-muted-foreground">
                Loading alert history...
              </span>
            </div>
          ) : alertHistory && alertHistory.length > 0 ? (
            <div className="max-h-64 overflow-y-auto">
              <div className="divide-y divide-border">
                {alertHistory.map((alert) => (
                  <div
                    key={alert.id}
                    className="py-3 px-1 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        {getNotificationStatusIcon(alert.status)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-foreground text-sm line-clamp-1">
                            {alert.title}
                          </p>
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-xs flex-shrink-0',
                              alert.status === 'SENT'
                                ? 'text-green-600 border-green-600'
                                : alert.status === 'FAILED'
                                  ? 'text-red-600 border-red-600'
                                  : 'text-yellow-600 border-yellow-600',
                            )}
                          >
                            {alert.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                          {alert.message}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{formatTriggerDate(alert.created_at)}</span>
                          {alert.transaction_id && (
                            <>
                              <span>•</span>
                              <span>Txn: {alert.transaction_id.slice(0, 8)}...</span>
                            </>
                          )}
                          <span>•</span>
                          <span className="capitalize">
                            {alert.notification_method.toLowerCase()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-4 text-sm text-muted-foreground">
              No alert history available
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
