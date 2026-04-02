import { Suspense } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { StatCard, StatCardSkeleton } from '@/design-system/data-display/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import { Wallet, TrendingUp, BarChart3, Activity } from 'lucide-react';
import Link from 'next/link';

export const metadata = { title: 'Dashboard' };

function PortfolioStats() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="Portfolio Value"
        value="IDR 1.234.567.890"
        delta="IDR 12.345.678"
        deltaType="positive"
        subtitle="vs IHSG: +8.2%"
        icon={Wallet}
      />
      <StatCard
        label="Day P&L"
        value="+IDR 12.345.678"
        delta="+1.28%"
        deltaType="positive"
        icon={TrendingUp}
      />
      <StatCard
        label="Total Return"
        value="+23.45%"
        delta="YTD"
        deltaType="positive"
        subtitle="Annualized: +31.2%"
        icon={BarChart3}
      />
      <StatCard
        label="Sharpe Ratio"
        value="1.84"
        delta="Sortino: 2.41"
        deltaType="neutral"
        subtitle="Calmar: 1.92"
        icon={Activity}
      />
    </div>
  );
}

function EquityCurvePlaceholder() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Equity Curve</CardTitle>
          <div className="flex gap-1">
            {['1W', '1M', '3M', '1Y', 'All'].map((period) => (
              <button
                key={period}
                className="rounded px-2 py-0.5 text-xs text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
              >
                {period}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex h-64 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
          Chart loads with lightweight-charts
        </div>
      </CardContent>
    </Card>
  );
}

function TopMovers() {
  const movers = [
    { symbol: 'BBCA', change: 2.3 },
    { symbol: 'TLKM', change: -1.1 },
    { symbol: 'BMRI', change: 0.8 },
    { symbol: 'ASII', change: -0.5 },
    { symbol: 'BBRI', change: 1.6 },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Movers</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {movers.map((m) => (
            <Link
              key={m.symbol}
              href={`/markets/${m.symbol}`}
              className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-[var(--surface-3)]"
            >
              <span className="text-sm font-medium text-[var(--text-primary)]">{m.symbol}</span>
              <span
                className={`tabular-nums text-sm font-medium ${m.change > 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}
              >
                {m.change > 0 ? '+' : ''}{m.change.toFixed(1)}%
              </span>
            </Link>
          ))}
        </div>
        <Link href="/portfolio/positions" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">
          View all positions →
        </Link>
      </CardContent>
    </Card>
  );
}

function ActiveSignals() {
  const signals = [
    { symbol: 'BMRI', direction: 'buy' as const, confidence: 0.87 },
    { symbol: 'ASII', direction: 'hold' as const, confidence: 0.62 },
    { symbol: 'UNVR', direction: 'sell' as const, confidence: 0.91 },
  ];

  const directionColors = {
    buy: 'positive',
    sell: 'negative',
    hold: 'warning',
  } as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Signals</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {signals.map((s) => (
            <div key={s.symbol} className="flex items-center justify-between rounded-md px-2 py-1.5">
              <div className="flex items-center gap-2">
                <Badge variant={directionColors[s.direction]}>{s.direction.toUpperCase()}</Badge>
                <span className="text-sm font-medium text-[var(--text-primary)]">{s.symbol}</span>
              </div>
              <span className="tabular-nums text-xs text-[var(--text-secondary)]">
                conf: {s.confidence.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        <Link href="/research/signals" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">
          View all signals →
        </Link>
      </CardContent>
    </Card>
  );
}

function RecentOrders() {
  const orders = [
    { id: '1', symbol: 'BBCA', side: 'buy', qty: 500, price: 9875, status: 'filled', time: '14:32' },
    { id: '2', symbol: 'TLKM', side: 'sell', qty: 1000, price: 3850, status: 'filled', time: '14:28' },
    { id: '3', symbol: 'BMRI', side: 'buy', qty: 300, price: 6225, status: 'new', time: '14:15' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Orders</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          <div className="grid grid-cols-5 gap-2 px-2 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            <span>Symbol</span><span>Side</span><span>Qty</span><span>Price</span><span>Status</span>
          </div>
          {orders.map((o) => (
            <div key={o.id} className="grid grid-cols-5 gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-[var(--surface-3)]">
              <span className="font-medium text-[var(--text-primary)]">{o.symbol}</span>
              <Badge variant={o.side === 'buy' ? 'positive' : 'negative'} className="w-fit">{o.side}</Badge>
              <span className="tabular-nums text-[var(--text-secondary)]">{o.qty}</span>
              <span className="tabular-nums text-[var(--text-secondary)]">{o.price.toLocaleString('id-ID')}</span>
              <Badge variant={o.status === 'filled' ? 'positive' : 'info'}>{o.status}</Badge>
            </div>
          ))}
        </div>
        <Link href="/portfolio/orders" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">
          View all orders →
        </Link>
      </CardContent>
    </Card>
  );
}

function StrategyStatus() {
  const strategies = [
    { name: 'MomentumIDX', status: 'running', pnl: '+4.2%', trades: 28 },
    { name: 'PairsTrade', status: 'paused', pnl: '+1.8%', trades: 12 },
    { name: 'MeanRev', status: 'error', pnl: '-0.3%', trades: 5 },
  ];

  const statusVariant = { running: 'positive', paused: 'warning', error: 'negative' } as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Strategy Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {strategies.map((s) => (
            <div key={s.name} className="flex items-center justify-between rounded-md px-2 py-1.5">
              <div className="flex items-center gap-2">
                <Badge variant={statusVariant[s.status as keyof typeof statusVariant]}>{s.status}</Badge>
                <span className="text-sm font-medium text-[var(--text-primary)]">{s.name}</span>
              </div>
              <span className="tabular-nums text-xs text-[var(--text-secondary)]">
                P&L: {s.pnl} | {s.trades} trades
              </span>
            </div>
          ))}
        </div>
        <Link href="/strategies" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">
          View all strategies →
        </Link>
      </CardContent>
    </Card>
  );
}

function SystemHealth() {
  return (
    <Card>
      <CardContent className="py-3">
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--positive)]" />
            <span className="text-[var(--text-tertiary)]">API: 45ms</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--positive)]" />
            <span className="text-[var(--text-tertiary)]">WS: Connected</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--positive)]" />
            <span className="text-[var(--text-tertiary)]">Data: Fresh (2s)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--positive)]" />
            <span className="text-[var(--text-tertiary)]">Broker: Alpaca Paper</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-tertiary)]" />
            <span className="text-[var(--text-tertiary)]">Kill Switch: Inactive</span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Portfolio overview and command center"
      />

      <Suspense fallback={<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}</div>}>
        <PortfolioStats />
      </Suspense>

      <EquityCurvePlaceholder />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TopMovers />
        <ActiveSignals />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RecentOrders />
        <StrategyStatus />
      </div>

      <SystemHealth />
      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
