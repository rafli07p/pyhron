'use client';

import { PAPER_TRADING, GUARDRAILS, RECENT_ORDERS } from '@/mocks/terminal-data';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';

function fmt(n: number, decimals = 0) {
  return n.toLocaleString('en-US', { maximumFractionDigits: decimals });
}
function fmtM(n: number) {
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  return fmt(n);
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-[#1e1e22] bg-white/[0.02] p-3">
      <div className="text-[10px] uppercase tracking-wider text-white/30">{label}</div>
      <div className={`mt-1 font-mono text-sm font-semibold ${color ?? 'text-white/90'}`}>{value}</div>
    </div>
  );
}

function GuardrailBar({ label, current, limit, unit }: { label: string; current: number; limit: number; unit?: string }) {
  const pct = Math.round((Math.abs(current) / Math.abs(limit)) * 100);
  const color = pct >= 80 ? 'bg-red-500' : pct >= 50 ? 'bg-amber-500' : 'bg-emerald-500';
  const c = unit === 'M' ? fmtM(Math.abs(current)) : fmt(Math.abs(current));
  const l = unit === 'M' ? fmtM(Math.abs(limit)) : fmt(Math.abs(limit));

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-white/50">{label}</span>
        <span className="font-mono text-white/60">{c} / {l} ({pct}%)</span>
      </div>
      <div className="h-1.5 w-full rounded bg-white/[0.06]">
        <div className={`h-full rounded ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

export default function ExecutionPage() {
  const pt = PAPER_TRADING;
  const g = GUARDRAILS;

  const statsRows = [
    [
      { label: 'Connection', value: pt.connection, color: 'text-emerald-400' },
      { label: 'Active Strategies', value: String(pt.activeStrategies) },
      { label: 'Paper P&L MTD', value: `+${fmtM(pt.pnlMtd)} (${pt.pnlMtdPct}%)`, color: 'text-emerald-400' },
      { label: 'Total Trades', value: String(pt.totalTrades) },
    ],
    [
      { label: 'Avg Trades/Day', value: String(pt.avgTradesDay) },
      { label: 'Avg Hold Time', value: `${pt.avgHoldMin}m` },
      { label: 'Largest Win', value: `+${fmtM(pt.largestWin)}`, color: 'text-emerald-400' },
      { label: 'Largest Loss', value: fmtM(pt.largestLoss), color: 'text-red-400' },
    ],
    [
      { label: 'Profit Factor', value: String(pt.profitFactor) },
      { label: 'Sharpe', value: String(pt.sharpe) },
      { label: 'Win Rate', value: `${pt.winRate}%` },
      { label: 'Days Active', value: String(pt.daysActive) },
    ],
  ];

  return (
    <div className="flex min-h-full flex-col gap-3 p-4">
      <h1 className="text-sm font-semibold text-white/90">Execution</h1>

      {/* Paper Trading Stats */}
      <div className="flex flex-col gap-2">
        {statsRows.map((row, i) => (
          <div key={i} className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            {row.map((s) => (
              <StatCard key={s.label} label={s.label} value={s.value} color={s.color} />
            ))}
          </div>
        ))}
      </div>

      {/* Paper Trades Table */}
      <div className="overflow-x-auto rounded-lg border border-[#1e1e22]">
        <div className="border-b border-[#1e1e22] bg-white/[0.02] px-3 py-2 text-[10px] uppercase tracking-wider text-white/30">
          Paper Trades
        </div>
        <table className="w-full text-xs text-white/70">
          <thead className="border-b border-[#1e1e22] bg-white/[0.02]">
            <tr>
              {['ID', 'Time', 'Side', 'Symbol', 'Qty', 'Price', 'Status', 'Strategy'].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-[10px] uppercase tracking-wider text-white/30">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RECENT_ORDERS.map((o) => (
              <tr key={o.id} className="border-b border-[#1e1e22] hover:bg-white/[0.02]">
                <td className="px-3 py-2.5 font-mono text-white/40">{o.id}</td>
                <td className="px-3 py-2.5 font-mono">{o.time}</td>
                <td className={`px-3 py-2.5 font-mono font-medium ${o.side === 'BUY' ? 'text-blue-400' : 'text-red-400'}`}>
                  {o.side}
                </td>
                <td className="px-3 py-2.5 font-medium text-white/90">{o.symbol}</td>
                <td className="px-3 py-2.5 font-mono">{fmt(o.qty)}</td>
                <td className="px-3 py-2.5 font-mono">{fmt(o.price)}</td>
                <td className="px-3 py-2.5">
                  <span className={`text-[10px] ${o.status === 'filled' ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {o.status}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-white/40">{o.strategy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Guardrails */}
      <div className="rounded-lg border border-[#1e1e22] bg-white/[0.02] p-3">
        <div className="mb-3 text-[10px] uppercase tracking-wider text-white/30">Guardrails</div>
        <div className="flex flex-col gap-3">
          <GuardrailBar label="Max Position" current={g.maxPosition.current} limit={g.maxPosition.limit} unit="M" />
          <GuardrailBar label="Daily Loss" current={g.dailyLoss.current} limit={g.dailyLoss.limit} unit="M" />
          <GuardrailBar label="Open Orders" current={g.openOrders.current} limit={g.openOrders.limit} />
          <GuardrailBar label="Max Order Value" current={g.maxOrderValue.current} limit={g.maxOrderValue.limit} unit="M" />
          <div className="mt-1 flex gap-6 text-xs">
            <span>
              <span className="text-emerald-400">●</span>{' '}
              <span className="text-white/50">Circuit Breaker:</span>{' '}
              <span className="text-emerald-400">Armed</span>
            </span>
            <span>
              <span className="text-white/20">○</span>{' '}
              <span className="text-white/50">Kill Switch:</span>{' '}
              <span className="text-white/30">Inactive</span>
            </span>
          </div>
        </div>
      </div>

      <TerminalDisclaimer />
    </div>
  );
}
