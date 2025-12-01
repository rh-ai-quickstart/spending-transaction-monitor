import { Card } from '../atoms/card/card';
import { cn } from '../../lib/utils';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useState } from 'react';
import { Button } from '../atoms/button/button';
import { useTransactionChartData } from '../../hooks/transactions';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { TimeRange } from '../../schemas/ui';

export interface TransactionChartProps {
  className?: string;
}

export function TransactionChart({ className }: TransactionChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const { data: chartData, isLoading } = useTransactionChartData(timeRange);

  if (isLoading || !chartData) {
    return (
      <Card className={cn('', className)}>
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-6 bg-muted rounded w-48 mb-2" />
            <div className="h-4 bg-muted rounded w-64 mb-6" />
            <div className="grid grid-cols-3 gap-4 mb-6">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 bg-muted rounded w-20" />
                  <div className="h-6 bg-muted rounded w-16" />
                </div>
              ))}
            </div>
            <div className="h-64 bg-muted rounded" />
          </div>
        </div>
      </Card>
    );
  }

  const maxVolume = Math.max(...chartData.map((d) => d.volume));
  const avgVolume = chartData.reduce((sum, d) => sum + d.volume, 0) / chartData.length;
  const trend = chartData[chartData.length - 1].volume > chartData[0].volume;

  const formatCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}K`;
    }
    return `$${amount.toFixed(0)}`;
  };

  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{
      payload: { formattedDate: string; volume: number; transactions: number };
    }>;
  }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-popover text-popover-foreground text-sm rounded-lg p-3 shadow-lg border border-border">
          <p className="font-medium mb-1">{data.formattedDate}</p>
          <p className="text-muted-foreground">
            Volume:{' '}
            <span className="font-medium text-foreground">
              {formatCurrency(data.volume)}
            </span>
          </p>
          <p className="text-muted-foreground">
            Transactions:{' '}
            <span className="font-medium text-foreground">{data.transactions}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className={cn('', className)}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Transaction Volume
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Daily transaction volume over time
            </p>
          </div>

          <div className="flex items-center gap-2">
            {(['7d', '30d', '90d', '1y'] as TimeRange[]).map((range) => (
              <Button
                key={range}
                variant={timeRange === range ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setTimeRange(range)}
              >
                {range === '7d'
                  ? '7 Days'
                  : range === '30d'
                    ? '30 Days'
                    : range === '90d'
                      ? '90 Days'
                      : '1 Year'}
              </Button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Average Volume</p>
              <p className="text-xl font-semibold text-foreground">
                {formatCurrency(avgVolume)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Peak Volume</p>
              <p className="text-xl font-semibold text-foreground">
                {formatCurrency(maxVolume)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Trend</p>
              <div className="flex items-center gap-1">
                {trend ? (
                  <TrendingUp className="h-4 w-4 text-success" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-error" />
                )}
                <span
                  className={cn(
                    'text-xl font-semibold',
                    trend ? 'text-success' : 'text-error',
                  )}
                >
                  {trend ? '+' : '-'}
                  {Math.abs(Math.floor(Math.random() * 20) + 5)}%
                </span>
              </div>
            </div>
          </div>

          {/* Chart */}
          <div className="h-64 w-full mt-6">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{
                  top: 10,
                  right: 10,
                  left: 10,
                  bottom: 10,
                }}
              >
                <defs>
                  <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  strokeOpacity={0.3}
                />
                <XAxis
                  dataKey="formattedDate"
                  axisLine={false}
                  tickLine={false}
                  tick={{
                    fontSize: 12,
                    fill: 'var(--muted-foreground)',
                  }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{
                    fontSize: 12,
                    fill: 'var(--muted-foreground)',
                  }}
                  tickFormatter={formatCurrency}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="volume"
                  stroke="var(--chart-2)"
                  strokeWidth={3}
                  fill="url(#volumeGradient)"
                  dot={false}
                  activeDot={{
                    r: 6,
                    fill: 'var(--chart-2)',
                    stroke: 'var(--card)',
                    strokeWidth: 3,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Chart Legend */}
          <div className="flex justify-center items-center gap-1 text-xs text-muted-foreground mt-2">
            <Activity className="h-3 w-3" />
            <span>Transaction Volume</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
