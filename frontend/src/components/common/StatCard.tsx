import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: LucideIcon;
}

export default function StatCard({ title, value, change, changeLabel, icon: Icon }: StatCardProps) {
  const isPositive = change !== undefined && change >= 0;

  return (
    <div className="stat-card">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </p>
        {Icon && (
          <div className="p-2 rounded-lg bg-slate-800/60">
            <Icon className="h-4 w-4 text-slate-400" />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-slate-100 mb-1">{value}</p>
      {change !== undefined && (
        <div className="flex items-center gap-1.5">
          {isPositive ? (
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <TrendingDown className="h-3.5 w-3.5 text-red-400" />
          )}
          <span
            className={`text-sm font-medium ${
              isPositive ? 'text-emerald-400' : 'text-red-400'
            }`}
          >
            {isPositive ? '+' : ''}
            {change.toFixed(2)}%
          </span>
          {changeLabel && (
            <span className="text-xs text-slate-500 ml-1">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
