'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

interface MonthlyReturnData {
  month: string; // "2024-01" format
  return: number;
}

interface MonthlyReturnsProps {
  data: MonthlyReturnData[];
  height?: number;
  className?: string;
}

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function getReturnColor(value: number): string {
  if (value <= -5) return '#991b1b';
  if (value <= -3) return '#b91c1c';
  if (value <= -1) return '#dc2626';
  if (value < 0) return 'rgba(239,68,68,0.5)';
  if (value === 0) return '#3f3f46';
  if (value < 1) return 'rgba(34,197,94,0.5)';
  if (value < 3) return '#22c55e';
  if (value < 5) return '#16a34a';
  return '#166534';
}

function MonthlyReturns({ data, height = 300, className }: MonthlyReturnsProps) {
  const { years, grid } = useMemo(() => {
    if (data.length === 0) return { years: [] as string[], grid: new Map<string, number>() };

    const grid = new Map<string, number>();
    const yearSet = new Set<string>();

    for (const d of data) {
      grid.set(d.month, d.return);
      const year = d.month.split('-')[0];
      if (year) yearSet.add(year);
    }

    const years = Array.from(yearSet).sort();
    return { years, grid };
  }, [data]);

  if (data.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No monthly return data available</p>
      </Card>
    );
  }

  return (
    <div
      className={cn(
        'overflow-auto rounded-lg border border-[var(--border-default)] bg-[var(--surface-0)] p-3',
        className,
      )}
      style={{ height }}
      aria-label="Monthly returns heatmap"
      role="img"
    >
      <table className="w-full border-collapse" style={{ fontFamily: "'Geist Mono', monospace" }}>
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-xs font-medium text-[var(--text-tertiary)]">Year</th>
            {MONTH_LABELS.map((m) => (
              <th key={m} className="px-1 py-1 text-center text-xs font-medium text-[var(--text-tertiary)]">
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((year) => (
            <tr key={year}>
              <td className="px-2 py-1 text-xs font-medium text-[var(--text-secondary)]">{year}</td>
              {MONTH_LABELS.map((_, monthIdx) => {
                const key = `${year}-${String(monthIdx + 1).padStart(2, '0')}`;
                const value = grid.get(key);
                const hasData = value !== undefined;

                return (
                  <td key={monthIdx} className="px-0.5 py-0.5">
                    <div
                      className="flex items-center justify-center rounded-sm"
                      style={{
                        backgroundColor: hasData ? getReturnColor(value) : 'transparent',
                        minHeight: '28px',
                      }}
                    >
                      {hasData && (
                        <span
                          className="tabular-nums text-[10px] font-medium text-[var(--text-primary)]"
                          style={{ opacity: 0.9 }}
                        >
                          {value >= 0 ? '+' : ''}{value.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MonthlyReturnsSkeleton({ height = 300, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('p-4', className)} style={{ height }}>
      <div className="space-y-2">
        <div className="flex gap-1">
          <Skeleton className="h-4 w-10" />
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
        {Array.from({ length: 5 }).map((_, row) => (
          <div key={row} className="flex gap-1">
            <Skeleton className="h-7 w-10" />
            {Array.from({ length: 12 }).map((_, i) => (
              <Skeleton key={i} className="h-7 flex-1 rounded-sm" />
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

export { MonthlyReturns, MonthlyReturnsSkeleton };
export type { MonthlyReturnData };
