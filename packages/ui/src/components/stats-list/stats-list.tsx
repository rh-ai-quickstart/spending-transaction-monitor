import { StatCard } from '../stat-card/stat-card';
import { cn } from '../../lib/utils';
import type { Stat } from '../../schemas/ui';

// Re-export Stat for backwards compatibility
export type { Stat } from '../../schemas/ui';

export interface StatsListProps {
  className?: string;
  stats: Stat[];
  variant?: 'default' | 'compact';
  columns?: number;
}

export function StatsList({
  className,
  stats,
  variant = 'default',
  columns = 3,
}: StatsListProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'sm:grid-cols-2',
    3: 'sm:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-4',
    5: 'md:grid-cols-3 lg:grid-cols-5',
    6: 'md:grid-cols-3 lg:grid-cols-6',
  };

  const gridClass =
    columns <= 6 ? gridCols[columns as keyof typeof gridCols] : 'sm:grid-cols-3';

  return (
    <section className={cn('grid gap-4', gridClass, className)}>
      {stats.map((stat) => (
        <StatCard
          key={stat.id}
          title={stat.title}
          value={stat.value}
          variant={variant}
          tone={stat.tone}
          icon={stat.icon}
          action={stat.action}
          description={stat.description}
        />
      ))}
    </section>
  );
}
