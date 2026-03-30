'use client';

import { MetricCard } from './MetricCard';
import { PnLChart } from '@/components/charts/PnLChart';

const metrics = [
  { label: 'NAV', value: 'Rp 1.25B', change: 2.34 },
  { label: 'Daily Return', value: '+0.45%', change: 0.45 },
  { label: 'Max Drawdown', value: '-4.2%', change: -4.2 },
  { label: 'Active Strategies', value: '2', change: null },
];

const recentAlerts = [
  { time: '14:32', message: 'BBCA position hit target weight (8.5%)', type: 'info' },
  { time: '11:15', message: 'Momentum signal: Buy ADRO (rank 3/30)', type: 'signal' },
  { time: '09:45', message: 'Market open: IHSG +0.35% at open', type: 'info' },
  { time: 'Yesterday', message: 'Daily rebalance completed: 4 trades executed', type: 'info' },
];

export function DashboardOverview() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-medium text-text-primary">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((m) => (
          <MetricCard key={m.label} label={m.label} value={m.value} change={m.change} />
        ))}
      </div>

      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">P&L Chart</h3>
        <PnLChart />
      </div>

      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">Recent Alerts</h3>
        <div className="space-y-3">
          {recentAlerts.map((alert, i) => (
            <div key={i} className="flex items-start gap-3 text-sm">
              <span className="text-xs text-text-muted whitespace-nowrap w-16">{alert.time}</span>
              <span className="text-text-secondary">{alert.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
