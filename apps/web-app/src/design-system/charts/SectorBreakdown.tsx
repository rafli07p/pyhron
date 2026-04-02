'use client';

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

interface SectorData {
  name: string;
  value: number;
  color?: string;
}

interface SectorBreakdownProps {
  data: SectorData[];
  height?: number;
  className?: string;
}

const DEFAULT_COLORS = [
  '#2563eb',
  '#7c3aed',
  '#06b6d4',
  '#22c55e',
  '#eab308',
  '#f97316',
  '#ef4444',
  '#ec4899',
  '#6366f1',
  '#14b8a6',
  '#84cc16',
  '#f59e0b',
];

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { total?: number }; value?: number; name?: string }> }) {
  if (!active || !payload?.length) return null;

  const entry = payload[0];
  if (!entry) return null;

  const total = entry.payload?.total ?? 0;
  const value = entry.value ?? 0;
  const pct = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';

  return (
    <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-2 shadow-lg">
      <p className="mb-1 text-xs font-medium text-[var(--text-primary)]">{entry.name}</p>
      <p className="text-sm text-[var(--text-secondary)]">
        Value: {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value)}
      </p>
      <p className="text-sm text-[var(--text-secondary)]">
        Weight: {pct}%
      </p>
    </div>
  );
}

function CustomLegend({ payload }: { payload?: Array<{ value: string; color: string }> }) {
  if (!payload) return null;

  return (
    <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 pt-2">
      {payload.map((entry) => (
        <div key={entry.value} className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: entry.color }} />
          <span className="text-xs text-[var(--text-secondary)]">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

function SectorBreakdown({ data, height = 300, className }: SectorBreakdownProps) {
  if (data.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No sector data available</p>
      </Card>
    );
  }

  const total = data.reduce((sum, d) => sum + d.value, 0);
  const chartData = data.map((d) => ({ ...d, total }));

  return (
    <div
      className={cn('rounded-lg border border-[var(--border-default)] bg-[var(--surface-0)] p-2', className)}
      style={{ height }}
      aria-label="Sector breakdown donut chart"
      role="img"
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="45%"
            innerRadius="55%"
            outerRadius="80%"
            dataKey="value"
            nameKey="name"
            paddingAngle={2}
            stroke="none"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={entry.name}
                fill={entry.color ?? DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function SectorBreakdownSkeleton({ height = 300, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('flex flex-col items-center justify-center p-4', className)} style={{ height }}>
      <Skeleton className="h-40 w-40 rounded-full" />
      <div className="mt-4 flex gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-16" />
        ))}
      </div>
    </Card>
  );
}

export { SectorBreakdown, SectorBreakdownSkeleton };
export type { SectorData };
