'use client';

import { useState, useEffect, useMemo } from 'react';
import { StatCard, StatCardSkeleton } from '@/design-system/data-display/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { MiniChart } from '@/design-system/charts/MiniChart';
import { EquityCurve, type EquityDataPoint } from '@/design-system/charts/EquityCurve';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import { formatIDR, formatPercent, formatRelativeTime } from '@/lib/format';
import { Wallet, TrendingUp, BarChart3, Activity } from 'lucide-react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const STOCK_NAMES: Record<string, string> = {
  BBCA: 'Bank Central Asia', BMRI: 'Bank Mandiri', TLKM: 'Telkom Indonesia',
  ASII: 'Astra International', UNVR: 'Unilever Indonesia', BBRI: 'Bank Rakyat Indonesia',
  GOTO: 'GoTo Gojek Tokopedia',
};

interface Position {
  symbol: string; quantity: number; avg_price: number; last_price: number;
  market_value: number; unrealized_pnl: number; unrealized_pnl_pct: number;
}
interface Order {
  id: string; symbol: string; side: string; type: string; price: number;
  quantity: number; filled_qty: number; status: string; created_at: string;
}
interface PnLEntry { date: string; daily_pnl: number; cumulative_pnl: number; }

function getGreeting(): string {
  const h = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' })).getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function getMarketStatus(): { label: string; open: boolean } {
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' }));
  const h = now.getHours();
  const d = now.getDay();
  const open = d >= 1 && d <= 5 && h >= 9 && h < 16;
  return { label: open ? 'Market Open' : 'Market Closed', open };
}

function genSparkline(base: number, n = 20): number[] {
  const pts: number[] = [base];
  for (let i = 1; i < n; i++) pts.push(pts[i - 1]! * (1 + (Math.random() - 0.48) * 0.02));
  return pts;
}

const STATUS_BADGE: Record<string, 'positive' | 'info' | 'default' | 'warning'> = {
  filled: 'positive', open: 'info', cancelled: 'default', partial_fill: 'warning',
};

const strategies = [
  { name: 'MomentumIDX', status: 'running', color: 'bg-[var(--positive)]', pnl: '+4.2%', trades: 28 },
  { name: 'PairsTrade', status: 'paused', color: 'bg-amber-500', pnl: '+1.8%', trades: 12 },
  { name: 'MeanRev', status: 'error', color: 'bg-[var(--negative)]', pnl: '-0.3%', trades: 5 },
];

const periods = ['1W', '1M', '3M', '1Y'] as const;

export default function DashboardPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [totalPnl, setTotalPnl] = useState(0);
  const [cash, setCash] = useState(0);
  const [orders, setOrders] = useState<Order[]>([]);
  const [pnlHistory, setPnlHistory] = useState<PnLEntry[]>([]);
  const [returnPct, setReturnPct] = useState(0);
  const [sharpe, setSharpe] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activePeriod, setActivePeriod] = useState<string>('1M');

  useEffect(() => {
    async function load() {
      try {
        const [posRes, ordRes, pnlRes] = await Promise.all([
          fetch(`${API}/v1/trading/positions`), fetch(`${API}/v1/trading/orders`), fetch(`${API}/v1/trading/pnl`),
        ]);
        const posData = await posRes.json();
        const ordData = await ordRes.json();
        const pnlData = await pnlRes.json();
        setPositions(posData.positions);
        setTotalValue(posData.total_market_value);
        setTotalPnl(posData.total_unrealized_pnl);
        setCash(posData.cash_balance);
        setOrders(ordData.orders);
        setPnlHistory(pnlData.history);
        setReturnPct(pnlData.period_return_pct);
        setSharpe(pnlData.period_sharpe);
      } catch (e) { console.error('Dashboard fetch error', e); }
      setLoading(false);
    }
    load();
  }, []);

  const portfolioValue = totalValue + cash;
  const deltaType = (v: number): 'positive' | 'negative' | 'neutral' => v > 0 ? 'positive' : v < 0 ? 'negative' : 'neutral';
  const dayPct = portfolioValue ? (totalPnl / portfolioValue) * 100 : 0;

  const equityData: EquityDataPoint[] = useMemo(() => {
    if (!pnlHistory.length) return [];
    let peak = portfolioValue;
    let benchmarkVal = portfolioValue;
    return pnlHistory.map((e, i) => {
      const equity = portfolioValue + e.cumulative_pnl;
      if (equity > peak) peak = equity;
      const drawdown = ((equity - peak) / peak) * 100;
      // Deterministic pseudo-random noise based on index
      const noise = ((((i + 1) * 9301 + 49297) % 233280) / 233280) * 0.01 - 0.002;
      benchmarkVal *= 1 + noise;
      return { timestamp: Math.floor(new Date(e.date).getTime() / 1000), equity, drawdown, benchmark: benchmarkVal };
    });
  }, [pnlHistory, portfolioValue]);

  const sortedPositions = useMemo(
    () => [...positions].sort((a, b) => Math.abs(b.unrealized_pnl_pct) - Math.abs(a.unrealized_pnl_pct)),
    [positions],
  );

  const ms = getMarketStatus();

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{getGreeting()}, Demo</h1>
        <p className="mt-1 flex items-center gap-2 text-sm text-[var(--text-tertiary)]">
          <span className={`h-2 w-2 rounded-full ${ms.open ? 'bg-[var(--positive)]' : 'bg-[var(--text-tertiary)]'}`} />
          {ms.label} &middot; {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Stats */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Portfolio Value" value={formatIDR(portfolioValue)} delta={formatIDR(totalPnl)} deltaType={deltaType(totalPnl)} icon={Wallet} />
          <StatCard label="Day P&L" value={formatIDR(totalPnl)} delta={formatPercent(dayPct)} deltaType={deltaType(totalPnl)} icon={TrendingUp} />
          <StatCard label="Total Return" value={formatPercent(returnPct)} deltaType={deltaType(returnPct)} subtitle="vs IHSG" icon={BarChart3} />
          <StatCard label="Sharpe Ratio" value={sharpe.toFixed(2)} deltaType="neutral" icon={Activity} />
        </div>
      )}

      {/* Equity Curve */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Equity Curve</CardTitle>
            <div className="flex gap-1">
              {periods.map((p) => (
                <button key={p} onClick={() => setActivePeriod(p)}
                  className={`rounded px-2 py-0.5 text-xs ${activePeriod === p ? 'bg-[var(--accent-100)] text-[var(--accent-500)]' : 'text-[var(--text-tertiary)] hover:bg-[var(--surface-3)]'}`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-[300px] items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">Loading...</div>
          ) : (
            <EquityCurve data={equityData} height={300} />
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Top Movers */}
        <Card>
          <CardHeader><CardTitle>Top Movers</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sortedPositions.map((p) => (
                <Link key={p.symbol} href={`/markets/${p.symbol}`}
                  className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-[var(--surface-3)]">
                  <div className="flex items-center gap-3">
                    <div>
                      <span className="text-sm font-medium text-[var(--text-primary)]">{p.symbol}</span>
                      <span className="ml-2 text-xs text-[var(--text-tertiary)]">{STOCK_NAMES[p.symbol] ?? ''}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <MiniChart data={genSparkline(p.avg_price)} width={80} height={24} positive={p.unrealized_pnl_pct >= 0} />
                    <span className={`w-16 text-right tabular-nums text-sm font-medium ${p.unrealized_pnl_pct >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                      {p.unrealized_pnl_pct >= 0 ? '+' : ''}{p.unrealized_pnl_pct.toFixed(2)}%
                    </span>
                  </div>
                </Link>
              ))}
            </div>
            <Link href="/portfolio/positions" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">View all positions &rarr;</Link>
          </CardContent>
        </Card>

        {/* Strategy Status */}
        <Card>
          <CardHeader><CardTitle>Strategy Status</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {strategies.map((s) => (
                <div key={s.name} className="flex items-center justify-between rounded-md px-2 py-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${s.color}`} />
                    <span className="text-sm font-medium text-[var(--text-primary)]">{s.name}</span>
                    <span className="text-xs capitalize text-[var(--text-tertiary)]">{s.status}</span>
                  </div>
                  <span className="tabular-nums text-xs text-[var(--text-secondary)]">P&L: {s.pnl} | {s.trades} trades</span>
                </div>
              ))}
            </div>
            <Link href="/strategies" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">View all strategies &rarr;</Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Orders */}
      <Card>
        <CardHeader><CardTitle>Recent Orders</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  <th className="px-2 py-1">Time</th><th className="px-2 py-1">Symbol</th><th className="px-2 py-1">Side</th>
                  <th className="px-2 py-1">Type</th><th className="px-2 py-1">Qty</th><th className="px-2 py-1">Price</th><th className="px-2 py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id} className="hover:bg-[var(--surface-3)]">
                    <td className="px-2 py-1.5 text-[var(--text-tertiary)]">{formatRelativeTime(o.created_at)}</td>
                    <td className="px-2 py-1.5 font-medium text-[var(--text-primary)]">{o.symbol}</td>
                    <td className="px-2 py-1.5"><Badge variant={o.side === 'buy' ? 'positive' : 'negative'}>{o.side}</Badge></td>
                    <td className="px-2 py-1.5 text-[var(--text-secondary)]">{o.type}</td>
                    <td className="px-2 py-1.5 tabular-nums text-[var(--text-secondary)]">{o.quantity.toLocaleString('id-ID')}</td>
                    <td className="px-2 py-1.5 tabular-nums text-[var(--text-secondary)]">{o.price.toLocaleString('id-ID')}</td>
                    <td className="px-2 py-1.5"><Badge variant={STATUS_BADGE[o.status] ?? 'default'}>{o.status.replace('_', ' ')}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link href="/portfolio/orders" className="mt-3 block text-xs text-[var(--accent-500)] hover:underline">View all orders &rarr;</Link>
        </CardContent>
      </Card>

      {/* System Health */}
      <Card>
        <CardContent className="py-3">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            {[
              { label: 'API: 45ms', ok: true }, { label: 'WS: Connected', ok: true },
              { label: 'Data: Fresh (2s)', ok: true }, { label: 'Broker: Alpaca Paper', ok: true },
            ].map((s) => (
              <span key={s.label} className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${s.ok ? 'bg-[var(--positive)]' : 'bg-[var(--negative)]'}`} />
                <span className="text-[var(--text-tertiary)]">{s.label}</span>
              </span>
            ))}
          </div>
        </CardContent>
      </Card>

      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
