import { formatPct, pctColor } from '@/lib/utils/format';

interface MetricCardProps {
  label: string;
  value: string;
  change: number | null;
}

export function MetricCard({ label, value, change }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <p className="text-xs text-text-muted">{label}</p>
      <p className="mt-1 text-2xl font-medium font-mono text-text-primary">{value}</p>
      {change !== null && (
        <p className={`mt-1 text-xs font-mono ${pctColor(change)}`}>{formatPct(change)}</p>
      )}
    </div>
  );
}
