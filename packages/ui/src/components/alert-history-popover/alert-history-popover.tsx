/**
 * Alert History Popover Component
 * Shows recent alerts in a popover when notification bell is clicked
 */

import { Button } from '../atoms/button/button';
import { Badge } from '../atoms/badge/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from '../atoms/dropdown-menu/dropdown-menu';
import { cn } from '../../lib/utils';
import { useAlerts } from '../../hooks/alert';
import {
  Bell,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react';
import type { Alert } from '../../schemas/transaction';
import { Link } from '@tanstack/react-router';

export interface AlertHistoryPopoverProps {
  className?: string;
}

function getAlertIcon(severity: Alert['severity']) {
  switch (severity) {
    case 'high':
    case 'critical':
      return <XCircle className="h-4 w-4 text-red-600" />;
    case 'medium':
      return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
    case 'low':
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    default:
      return <Bell className="h-4 w-4 text-gray-600" />;
  }
}

function getSeverityBadgeColor(severity: Alert['severity']): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-200';
    case 'high':
      return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900 dark:text-orange-200';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-200';
    case 'low':
      return 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900 dark:text-green-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900 dark:text-gray-200';
  }
}

function formatAlertTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

  if (diffInHours < 1) {
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    return diffInMinutes < 1 ? 'Just now' : `${diffInMinutes}m ago`;
  } else if (diffInHours < 24) {
    return `${diffInHours}h ago`;
  } else {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }
}

export function AlertHistoryPopover({ className }: AlertHistoryPopoverProps) {
  const { data: alerts, isLoading } = useAlerts();

  // Sort alerts by timestamp (most recent first) and limit to recent ones
  const recentAlerts =
    alerts
      ?.slice()
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 10) || [];

  const unreadCount = alerts?.filter((alert) => !alert.resolved).length || 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn('relative rounded-full', className)}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-600 rounded-full flex items-center justify-center text-xs text-white font-medium">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-96 p-0" align="end">
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-foreground">Alert History</h3>
            <DropdownMenuItem asChild>
              <Link to="/alerts">
                <Button variant="ghost" size="sm" className="text-xs">
                  View All
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            </DropdownMenuItem>
          </div>
        </div>

        <div className="max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
              <span className="ml-2 text-sm text-muted-foreground">
                Loading alerts...
              </span>
            </div>
          ) : recentAlerts.length > 0 ? (
            <div className="divide-y divide-border">
              {recentAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className={cn(
                    'p-4 hover:bg-muted/50 transition-colors cursor-pointer',
                    !alert.resolved && 'bg-primary/5',
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {getAlertIcon(alert.severity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <p className="font-medium text-foreground text-sm truncate">
                          {alert.title}
                        </p>
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs flex-shrink-0',
                            getSeverityBadgeColor(alert.severity),
                          )}
                        >
                          {alert.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                        {alert.description}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{formatAlertTime(alert.timestamp)}</span>
                        {alert.transaction_id && (
                          <>
                            <span>•</span>
                            <span>ID: {alert.transaction_id.slice(0, 8)}...</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-sm text-muted-foreground">
              <Bell className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
              No alerts yet
            </div>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
