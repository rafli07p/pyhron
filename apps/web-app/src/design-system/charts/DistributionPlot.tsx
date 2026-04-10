'use client';

import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { cn } from '@/lib/utils';
import { Card } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

interface DistributionBin {
  bin: number;
  count: number;
}

interface DistributionPlotProps {
  data: DistributionBin[];
  mean: number;
  stddev: number;
  height?: number;
  className?: string;
}

function normalPdf(x: number, mean: number, stddev: number): number {
  if (stddev === 0) return 0;
  const exponent = -0.5 * ((x - mean) / stddev) ** 2;
  return (1 / (stddev * Math.sqrt(2 * Math.PI))) * Math.exp(exponent);
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: DistributionBin & { normal: number } }> }) {
  if (!active || !payload?.length) return null;

  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-2 shadow-lg">
      <p className="mb-1 text-xs text-[var(--text-tertiary)]">
        Return: {data.bin >= 0 ? '+' : ''}{data.bin.toFixed(2)}%
      </p>
      <p className="text-sm font-medium text-[var(--text-primary)]">
        Count: {data.count}
      </p>
    </div>
  );
}

function DistributionPlot({ data, mean, stddev, height = 300, className }: DistributionPlotProps) {
  if (data.length === 0) {
    return (
      <Card className={cn('flex items-center justify-center p-4', className)} style={{ height }}>
        <p className="text-sm text-[var(--text-tertiary)]">No distribution data available</p>
      </Card>
    );
  }

  // Find the max count to scale the normal curve to match histogram height
  const maxCount = Math.max(...data.map((d) => d.count));
  const peakNormal = normalPdf(mean, mean, stddev);
  const scaleFactor = peakNormal > 0 ? maxCount / peakNormal : 1;

  const chartData = data.map((d) => ({
    ...d,
    normal: normalPdf(d.bin, mean, stddev) * scaleFactor,
  }));

  return (
    <div
      className={cn('rounded-lg border border-[var(--border-default)] bg-[var(--surface-0)] p-2', className)}
      style={{ height }}
      aria-label="Return distribution plot"
      role="img"
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <XAxis
            dataKey="bin"
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            stroke="#71717a"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
          />
          <YAxis
            stroke="#71717a"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            x={mean}
            stroke="#2563eb"
            strokeWidth={2}
            strokeDasharray="6 3"
            label={{
              value: `\u03BC=${mean.toFixed(2)}%`,
              position: 'top',
              fill: '#2563eb',
              fontSize: 11,
              fontFamily: "var(--font-mono), monospace",
            }}
          />
          <Bar
            dataKey="count"
            fill="rgba(37,99,235,0.5)"
            stroke="#2563eb"
            strokeWidth={1}
            radius={[2, 2, 0, 0]}
          />
          <Line
            type="monotone"
            dataKey="normal"
            stroke="#a1a1aa"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function DistributionPlotSkeleton({ height = 300, className }: { height?: number; className?: string }) {
  return (
    <Card className={cn('p-4', className)} style={{ height }}>
      <div className="flex h-full flex-col justify-between">
        <Skeleton className="h-4 w-32" />
        <div className="flex flex-1 items-end gap-1 px-2 pt-4">
          {Array.from({ length: 20 }).map((_, i) => {
            const mid = 10;
            const dist = Math.abs(i - mid);
            const h = Math.max(10, 80 - dist * dist);
            return (
              <Skeleton
                key={i}
                className="flex-1"
                style={{ height: `${h}%` }}
              />
            );
          })}
        </div>
        <Skeleton className="mt-2 h-3 w-full" />
      </div>
    </Card>
  );
}

export { DistributionPlot, DistributionPlotSkeleton };
export type { DistributionBin };
