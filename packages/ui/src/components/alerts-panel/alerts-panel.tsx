import { AlertTriangle, Info, AlertCircle, XCircle, Bell } from 'lucide-react';
import { Card } from '../atoms/card/card';
import { Button } from '../atoms/button/button';
import { Badge } from '../atoms/badge/badge';
import { cn } from '../../lib/utils';
import { severityColors } from '../../lib/colors';
import { useAlerts } from '../../hooks/alert';
import type { Alert } from '../../schemas/transaction';

export interface AlertsPanelProps {
  className?: string;
  onAlertClick?: (alert: Alert) => void;
}

export function AlertsPanel({ className, onAlertClick }: AlertsPanelProps) {
  const { data: alerts, isLoading } = useAlerts();

  const getSeverityIcon = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return XCircle;
      case 'high':
        return AlertTriangle;
      case 'medium':
        return AlertCircle;
      case 'low':
        return Info;
    }
  };

  const getSeverityColor = (severity: Alert['severity']) => {
    return severityColors[severity]?.icon || 'text-muted-foreground';
  };

  const getSeverityBadgeColor = (severity: Alert['severity']) => {
    return severityColors[severity]?.badge || 'bg-muted text-muted-foreground';
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;

    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="space-y-4">
          <div className="animate-pulse">
            <div className="h-5 bg-muted rounded w-32 mb-4" />
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-2 mb-4">
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  const activeAlerts = alerts?.filter((alert) => !alert.resolved) || [];
  const hasAlerts = activeAlerts.length > 0;

  return (
    <Card className={cn('', className)}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-foreground" />
            <h3 className="text-lg font-semibold text-foreground">Active Alerts</h3>
            {hasAlerts && (
              <Badge variant="secondary" className="ml-2">
                {activeAlerts.length}
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="sm">
            View All
          </Button>
        </div>

        {!hasAlerts ? (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-3">
              <Bell className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="text-muted-foreground text-sm">No active alerts</p>
            <p className="text-muted-foreground text-xs mt-1">
              Your transactions are looking good!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeAlerts.map((alert) => {
              const Icon = getSeverityIcon(alert.severity);

              return (
                <div
                  key={alert.id}
                  className={cn(
                    'p-4 rounded-lg border border-border',
                    'hover:bg-muted/50 transition-colors cursor-pointer',
                    'group',
                  )}
                  onClick={() => onAlertClick?.(alert)}
                >
                  <div className="flex items-start gap-3">
                    <Icon
                      className={cn('h-5 w-5 mt-0.5', getSeverityColor(alert.severity))}
                    />

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="font-medium text-foreground text-sm">
                          {alert.title}
                        </h4>
                        <Badge
                          variant="secondary"
                          className={cn(
                            'text-xs capitalize',
                            getSeverityBadgeColor(alert.severity),
                          )}
                        >
                          {alert.severity}
                        </Badge>
                      </div>

                      <p className="text-sm text-muted-foreground">
                        {alert.description}
                      </p>

                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatTime(alert.timestamp)}</span>
                        {alert.transaction_id && (
                          <>
                            <span>•</span>
                            <span>Transaction {alert.transaction_id}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}
