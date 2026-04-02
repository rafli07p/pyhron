import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral';
  subtitle?: string;
  icon?: LucideIcon;
  className?: string;
}

function StatCard({ label, value, delta, deltaType = 'neutral', subtitle, icon: Icon, className }: StatCardProps) {
  return (
    <Card className={cn('p-4', className)}>
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            {label}
          </p>
          <p className="tabular-nums text-2xl font-semibold text-[var(--text-primary)]">{value}</p>
          {delta && (
            <p
              className={cn('tabular-nums text-sm font-medium', {
                'text-[var(--positive)]': deltaType === 'positive',
                'text-[var(--negative)]': deltaType === 'negative',
                'text-[var(--text-secondary)]': deltaType === 'neutral',
              })}
            >
              {deltaType === 'positive' && '+'}{delta}
            </p>
          )}
          {subtitle && (
            <p className="text-xs text-[var(--text-tertiary)]">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className="rounded-md bg-[var(--accent-50)] p-2">
            <Icon className="h-4 w-4 text-[var(--accent-500)]" />
          </div>
        )}
      </div>
    </Card>
  );
}

function StatCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn('p-4', className)}>
      <div className="space-y-2">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-4 w-24" />
      </div>
    </Card>
  );
}

export { StatCard, StatCardSkeleton };
