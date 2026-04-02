'use client';

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

interface EquityDataPoint {
  timestamp: number;
  equity: number;
  drawdown: number;
  benchmark?: number;
}

interface EquityCurveProps {
  data: EquityDataPoint[];
  height?: number;
  className?: string;
}

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatCurrency(val: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(val);
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: EquityDataPoint }> }) {
  if (!active || !payload?.length) return null;

  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-2 shadow-lg">
      <p className="mb-1 text-xs text-[var(--text-tertiary)]">{formatDate(data.timestamp)}</p>
      <p className="text-sm font-medium text-[var(--text-primary)]">
        Equity: {formatCurrency(data.equity)}
      </p>
      <p
        className={cn('text-sm font-medium', {
          'text-[var(--negative)]': data.drawdown < 0,
          'text-[var(--text-secondary)]': data.drawdown >= 0,
        })}
      >
        Drawdown: {data.drawdown.toFixed(2)}%
      </p>
      {data.benchmark !== undefined && (
        <p className="text-sm text-[var(--text-secondary)]">
          Benchmark: {formatCurrency(data.benchmark)}
        </p>
      )}
    </div>
  );
}

function EquityCurve({ data, height = 300, className }: EquityCurveProps) {
  if (data.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No equity data available</p>
      </Card>
    );
  }

  const hasBenchmark = data.some((d) => d.benchmark !== undefined);

  return (
    <div
      className={cn('rounded-lg border border-[var(--border-default)] bg-[var(--surface-0)] p-2', className)}
      style={{ height }}
      aria-label="Portfolio equity curve"
      role="img"
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity={0} />
              <stop offset="100%" stopColor="#ef4444" stopOpacity={0.3} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(ts: number) =>
              new Date(ts * 1000).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
            }
            stroke="#71717a"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
          />
          <YAxis
            yAxisId="equity"
            orientation="right"
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            stroke="#71717a"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            yAxisId="drawdown"
            orientation="left"
            tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            stroke="#71717a"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            yAxisId="equity"
            type="monotone"
            dataKey="equity"
            stroke="#2563eb"
            strokeWidth={2}
            fill="url(#equityGrad)"
          />
          <Area
            yAxisId="drawdown"
            type="monotone"
            dataKey="drawdown"
            stroke="#ef4444"
            strokeWidth={1}
            fill="url(#drawdownGrad)"
          />
          {hasBenchmark && (
            <Line
              yAxisId="equity"
              type="monotone"
              dataKey="benchmark"
              stroke="#a1a1aa"
              strokeWidth={1.5}
              strokeDasharray="6 3"
              dot={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function EquityCurveSkeleton({ height = 300, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('p-4', className)} style={{ height }}>
      <div className="flex h-full flex-col justify-between">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-4 h-full w-full rounded-md" />
        <Skeleton className="mt-2 h-3 w-full" />
      </div>
    </Card>
  );
}

export { EquityCurve, EquityCurveSkeleton };
export type { EquityDataPoint };
