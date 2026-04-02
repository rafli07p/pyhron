'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { Badge } from '@/design-system/primitives/Badge';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { Plus, FlaskConical } from 'lucide-react';
import Link from 'next/link';

const recentBacktests = [
  { id: 'bt-1', strategy: 'MomentumIDX', dateRange: '2024-01-01 to 2025-12-31', totalReturn: '+42.3%', sharpe: 1.84, maxDD: '-12.4%', status: 'completed' as const },
  { id: 'bt-2', strategy: 'PairsTrade BBCA-BMRI', dateRange: '2024-06-01 to 2025-12-31', totalReturn: '+18.7%', sharpe: 1.42, maxDD: '-8.2%', status: 'completed' as const },
  { id: 'bt-3', strategy: 'MeanReversion LQ45', dateRange: '2023-01-01 to 2025-12-31', totalReturn: '+31.5%', sharpe: 1.23, maxDD: '-18.7%', status: 'completed' as const },
  { id: 'bt-4', strategy: 'Value Factor IDX', dateRange: '2025-01-01 to 2025-12-31', totalReturn: 'N/A', sharpe: 0, maxDD: 'N/A', status: 'running' as const },
  { id: 'bt-5', strategy: 'Sector Rotation', dateRange: '2024-01-01 to 2025-06-30', totalReturn: '-3.2%', sharpe: -0.21, maxDD: '-24.1%', status: 'failed' as const },
];

const statusVariant = {
  completed: 'positive',
  running: 'info',
  failed: 'negative',
} as const;

const columns = ['Strategy', 'Date Range', 'Total Return', 'Sharpe', 'Max DD', 'Status'];

export default function BacktestsPage() {
  const { hasAccess } = useTierGate('studio.backtests');

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <PageHeader title="Backtests" description="Run and analyze strategy backtests" />
        <TierGate requiredTier="strategist" featureName="Backtesting" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtests"
        description="Run and analyze strategy backtests"
        actions={
          <Link href="/studio/backtests/new">
            <Button variant="primary" size="sm">
              <Plus className="h-3.5 w-3.5" />
              New Backtest
            </Button>
          </Link>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-3.5 w-3.5" />
            Recent Backtests
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  {columns.map((col) => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentBacktests.map((bt) => (
                  <tr
                    key={bt.id}
                    className="border-b border-[var(--border-default)] transition-colors last:border-0 hover:bg-[var(--surface-2)]"
                  >
                    <td className="px-3 py-2">
                      <Link href={`/studio/backtests/${bt.id}`} className="text-sm font-medium text-[var(--accent-500)] hover:underline">
                        {bt.strategy}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-xs text-[var(--text-secondary)]">{bt.dateRange}</td>
                    <td className={`px-3 py-2 tabular-nums text-sm font-medium ${bt.totalReturn.startsWith('+') ? 'text-[var(--positive)]' : bt.totalReturn.startsWith('-') ? 'text-[var(--negative)]' : 'text-[var(--text-secondary)]'}`}>
                      {bt.totalReturn}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{bt.sharpe.toFixed(2)}</td>
                    <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{bt.maxDD}</td>
                    <td className="px-3 py-2">
                      <Badge variant={statusVariant[bt.status]}>{bt.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
