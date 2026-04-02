import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import Link from 'next/link';

export const metadata = { title: 'Strategies' };

export default function StrategiesPage() {
  const strategies = [
    { id: '1', name: 'MomentumIDX', type: 'momentum', status: 'running', mode: 'paper', pnl: 4.2, trades: 28, sharpe: 1.84, drawdown: -8.3 },
    { id: '2', name: 'PairsTrade BBCA-BMRI', type: 'pairs_trading', status: 'paused', mode: 'paper', pnl: 1.8, trades: 12, sharpe: 1.21, drawdown: -5.1 },
    { id: '3', name: 'ML Signal Alpha', type: 'ml_signal', status: 'running', mode: 'paper', pnl: 6.7, trades: 45, sharpe: 2.15, drawdown: -4.2 },
    { id: '4', name: 'MeanReversion', type: 'mean_reversion', status: 'error', mode: 'paper', pnl: -0.3, trades: 5, sharpe: -0.21, drawdown: -12.1 },
  ];

  const statusVariant: Record<string, 'positive' | 'warning' | 'negative' | 'info'> = {
    running: 'positive', paused: 'warning', error: 'negative', stopped: 'default' as 'info',
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Strategies"
        description="Strategy management console"
        actions={<Button size="sm" asChild><Link href="/strategies/builder">Strategy Builder</Link></Button>}
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {strategies.map((s) => (
          <Link key={s.id} href={`/strategies/${s.id}`}>
            <Card className="p-4 transition-colors hover:border-[var(--accent-500)]">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">{s.name}</h3>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant={statusVariant[s.status]}>{s.status}</Badge>
                    <Badge variant="outline">{s.type.replace('_', ' ')}</Badge>
                    <Badge variant="info">{s.mode}</Badge>
                  </div>
                </div>
                <span className={`tabular-nums text-lg font-semibold ${s.pnl > 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                  {s.pnl > 0 ? '+' : ''}{s.pnl}%
                </span>
              </div>
              <div className="mt-3 flex gap-4 text-xs text-[var(--text-tertiary)]">
                <span>Trades: {s.trades}</span>
                <span>Sharpe: {s.sharpe.toFixed(2)}</span>
                <span>Max DD: {s.drawdown}%</span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
