'use client';

import { use } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { StatCard } from '@/design-system/data-display/StatCard';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import {
  TrendingUp,
  BarChart3,
  Activity,
  ArrowDownRight,
  Target,
  Download,
} from 'lucide-react';

const metrics = [
  { label: 'Total Return', value: '+42.3%', deltaType: 'positive' as const, icon: TrendingUp },
  { label: 'CAGR', value: '19.8%', deltaType: 'positive' as const, icon: BarChart3 },
  { label: 'Sharpe Ratio', value: '1.84', deltaType: 'neutral' as const, icon: Activity },
  { label: 'Sortino Ratio', value: '2.41', deltaType: 'neutral' as const, icon: Activity },
  { label: 'Max Drawdown', value: '-12.4%', deltaType: 'negative' as const, icon: ArrowDownRight },
  { label: 'Win Rate', value: '58.3%', deltaType: 'positive' as const, icon: Target },
];

const tradeLogColumns = ['Date', 'Symbol', 'Side', 'Qty', 'Price', 'P&L'];

const sampleTrades = [
  { date: '2025-01-15', symbol: 'BBCA', side: 'BUY', qty: 500, price: 9200, pnl: '' },
  { date: '2025-02-03', symbol: 'BBCA', side: 'SELL', qty: 500, price: 9875, pnl: '+IDR 337,500' },
  { date: '2025-02-10', symbol: 'BMRI', side: 'BUY', qty: 1000, price: 5800, pnl: '' },
  { date: '2025-03-14', symbol: 'BMRI', side: 'SELL', qty: 1000, price: 6225, pnl: '+IDR 425,000' },
  { date: '2025-03-20', symbol: 'TLKM', side: 'BUY', qty: 2000, price: 4100, pnl: '' },
  { date: '2025-04-01', symbol: 'TLKM', side: 'SELL', qty: 2000, price: 3850, pnl: '-IDR 500,000' },
];

export default function BacktestDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { hasAccess } = useTierGate('studio.backtests');

  if (!hasAccess) {
    return (
      <div className="space-y-3">
        <PageHeader title="Backtest Detail" description={`Backtest: ${id}`} />
        <TierGate requiredTier="strategist" featureName="Backtesting" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title={`Backtest: ${id}`}
        description="MomentumIDX | 2024-01-01 to 2025-12-31"
        actions={
          <Button variant="outline" size="sm">
            <Download className="h-3.5 w-3.5" />
            Export Report
          </Button>
        }
      />

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((m) => (
          <StatCard
            key={m.label}
            label={m.label}
            value={m.value}
            deltaType={m.deltaType}
            icon={m.icon}
          />
        ))}
      </div>

      {/* Equity Curve */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
            Equity curve chart loads here
          </div>
        </CardContent>
      </Card>

      {/* Monthly Returns */}
      <Card>
        <CardHeader>
          <CardTitle>Monthly Returns</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
            Monthly returns heatmap loads here
          </div>
        </CardContent>
      </Card>

      {/* Trade Log */}
      <Card>
        <CardHeader>
          <CardTitle>Trade Log</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  {tradeLogColumns.map((col) => (
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
                {sampleTrades.map((t, i) => (
                  <tr
                    key={i}
                    className="border-b border-[var(--border-default)] transition-colors last:border-0 hover:bg-[var(--surface-2)]"
                  >
                    <td className="px-3 py-2 text-xs text-[var(--text-secondary)]">{t.date}</td>
                    <td className="px-3 py-2 text-sm font-medium text-[var(--text-primary)]">{t.symbol}</td>
                    <td className={`px-3 py-2 text-xs font-medium ${t.side === 'BUY' ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                      {t.side}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{t.qty.toLocaleString('id-ID')}</td>
                    <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{t.price.toLocaleString('id-ID')}</td>
                    <td className={`px-3 py-2 tabular-nums text-sm font-medium ${t.pnl.startsWith('+') ? 'text-[var(--positive)]' : t.pnl.startsWith('-') ? 'text-[var(--negative)]' : 'text-[var(--text-tertiary)]'}`}>
                      {t.pnl || '-'}
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
