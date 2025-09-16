import { createFileRoute, Link } from '@tanstack/react-router';
import { TransactionChart } from '../components/transaction-chart/transaction-chart';
import { TransactionList } from '../components/transaction-list/transaction-list';
import { AlertsPanel } from '../components/alerts-panel/alerts-panel';
import { StatsList } from '../components/stats-list/stats-list';
import { Card } from '../components/atoms/card/card';
import { Button } from '../components/atoms/button/button';
import { LocationCapture } from '../components/location/LocationCapture';
import { useHealth } from '../hooks/health';
import { useTransactionStats } from '../hooks/transactions';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import {
  Server,
  Database,
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { Alert } from '../schemas/transaction';
import type { Stat } from '../components/stats-list/stats-list';

export const Route = createFileRoute('/')({
  component: () => (
    <ProtectedRoute>
      <Index />
    </ProtectedRoute>
  ),
});

function Index() {
  const { data: healthData } = useHealth();
  const { data: transactionStatsData } = useTransactionStats();

  const handleAlertClick = (alert: Alert) => {
    console.log('Alert selected:', alert);
    // TODO: Show alert details or navigate to related transaction
  };

  // Helper functions
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const calculateChange = (current: number, previous: number) => {
    const change = ((current - previous) / previous) * 100;
    return {
      value: Math.abs(change).toFixed(1),
      isPositive: change > 0,
    };
  };

  // Create stats for system health
  const services = [
    {
      id: 'api',
      name: 'API Service',
      status:
        healthData?.find((s: { name: string }) => s.name === 'API')?.status ||
        'unknown',
      icon: <Server className="h-8 w-8 text-success" />,
    },
    {
      id: 'db',
      name: 'Database',
      status:
        healthData?.find((s: { name: string }) => s.name === 'Database')?.status ||
        'unknown',
      icon: <Database className="h-8 w-8 text-info" />,
    },
  ];

  const healthyCount = services.filter((s) => s.status === 'healthy').length;
  const totalServices = services.length;
  const overallStatus =
    healthyCount === totalServices
      ? 'Operational'
      : healthyCount > totalServices / 2
        ? 'Degraded'
        : 'Down';
  const statusTone =
    healthyCount === totalServices
      ? 'emerald'
      : healthyCount > totalServices / 2
        ? 'sky'
        : 'violet';

  const systemStats: Stat[] = [
    {
      id: 'overall',
      title: 'Overall Health',
      value: overallStatus,
      tone: statusTone,
    },
    {
      id: 'services',
      title: 'Services',
      value: `${totalServices} total`,
      tone: 'sky',
    },
    {
      id: 'healthy',
      title: 'Healthy',
      value: `${healthyCount}/${totalServices}`,
      tone: 'emerald',
    },
  ];

  // Create transaction stats for the main dashboard
  const transactionStats: Stat[] = transactionStatsData
    ? [
        {
          id: 'total-transactions',
          title: 'Total Transactions',
          value: formatNumber(transactionStatsData.totalTransactions),
          description: 'transactions this period',
          icon: <DollarSign className="h-4 w-4 text-muted-foreground" />,
          tone: 'sky',
          action: (() => {
            const change = calculateChange(
              transactionStatsData.totalTransactions,
              transactionStatsData.previousPeriod.totalTransactions,
            );
            return (
              <div className="mt-4 flex items-center gap-1">
                {change.isPositive ? (
                  <TrendingUp className="h-3 w-3 text-success" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-error" />
                )}
                <span
                  className={cn(
                    'text-xs font-medium',
                    change.isPositive ? 'text-success' : 'text-error',
                  )}
                >
                  {change.value}%
                </span>
                <span className="text-xs text-muted-foreground">from last period</span>
              </div>
            );
          })(),
        },
        {
          id: 'transaction-volume',
          title: 'Transaction Volume',
          value: formatCurrency(transactionStatsData.totalVolume),
          description: 'total volume processed',
          icon: <TrendingUp className="h-4 w-4 text-muted-foreground" />,
          tone: 'emerald',
          action: (() => {
            const change = calculateChange(
              transactionStatsData.totalVolume,
              transactionStatsData.previousPeriod.totalVolume,
            );
            return (
              <div className="mt-4 flex items-center gap-1">
                {change.isPositive ? (
                  <TrendingUp className="h-3 w-3 text-success" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-error" />
                )}
                <span
                  className={cn(
                    'text-xs font-medium',
                    change.isPositive ? 'text-success' : 'text-error',
                  )}
                >
                  {change.value}%
                </span>
                <span className="text-xs text-muted-foreground">from last period</span>
              </div>
            );
          })(),
        },
        {
          id: 'active-alerts',
          title: 'Active Alerts',
          value: transactionStatsData.activeAlerts.toString(),
          description: 'alerts requiring attention',
          icon: <AlertTriangle className="h-4 w-4 text-muted-foreground" />,
          tone: 'violet',
          action: (() => {
            const change = calculateChange(
              transactionStatsData.activeAlerts,
              transactionStatsData.previousPeriod.activeAlerts,
            );
            const isPositive = !change.isPositive; // Inverted for alerts (lower is better)
            return (
              <div className="mt-4 flex items-center gap-1">
                {isPositive ? (
                  <TrendingUp className="h-3 w-3 text-success" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-error" />
                )}
                <span
                  className={cn(
                    'text-xs font-medium',
                    isPositive ? 'text-success' : 'text-error',
                  )}
                >
                  {change.value}%
                </span>
                <span className="text-xs text-muted-foreground">from last period</span>
              </div>
            );
          })(),
        },
        {
          id: 'processing-time',
          title: 'Avg. Processing Time',
          value: `${transactionStatsData.avgProcessingTime.toFixed(1)}s`,
          description: 'average transaction time',
          icon: <TrendingDown className="h-4 w-4 text-muted-foreground" />,
          tone: 'sky',
          action: (() => {
            const change = calculateChange(
              transactionStatsData.avgProcessingTime,
              transactionStatsData.previousPeriod.avgProcessingTime,
            );
            const isPositive = !change.isPositive; // Inverted for processing time (lower is better)
            return (
              <div className="mt-4 flex items-center gap-1">
                {isPositive ? (
                  <TrendingUp className="h-3 w-3 text-success" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-error" />
                )}
                <span
                  className={cn(
                    'text-xs font-medium',
                    isPositive ? 'text-success' : 'text-error',
                  )}
                >
                  {change.value}%
                </span>
                <span className="text-xs text-muted-foreground">from last period</span>
              </div>
            );
          })(),
        },
      ]
    : [];

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Transaction Statistics */}
      <StatsList stats={transactionStats} variant="default" columns={4} />

      {/* Location-Based Fraud Detection */}
      <LocationCapture 
        onLocationCaptured={(location) => {
          console.log('Location captured for fraud detection:', location);
        }}
        onLocationDenied={() => {
          console.log('Location access denied - fraud detection limited');
        }}
        onLocationError={(error) => {
          console.error('Location capture error:', error);
        }}
        autoRequest={false}
      />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Chart and Transactions */}
        <div className="lg:col-span-2 space-y-6">
          <TransactionChart />
          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">
                  Recent Transactions
                </h3>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/transactions">View All</Link>
                </Button>
              </div>
              <TransactionList itemsPerPage={5} />
            </div>
          </Card>
        </div>

        {/* Right Column - Alerts */}
        <div className="space-y-6">
          <AlertsPanel onAlertClick={handleAlertClick} />

          {/* System Health */}
          <Card>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                System Health
              </h3>
              <StatsList stats={systemStats} variant="default" columns={1} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
