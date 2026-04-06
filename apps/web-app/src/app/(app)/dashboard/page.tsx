'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { PORTFOLIO, POSITIONS, RECENT_ORDERS, STRATEGIES, generateEquityCurve } from '@/mocks/terminal-data';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';

const idr = (v: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(v);
const equityData = generateEquityCurve(90);
const periods = ['1W', '1M', '3M', '1Y'] as const;

const statusIcon = (s: string) =>
  s === 'running' ? <span className="text-emerald-400">●</span>
  : s === 'paused' ? <span className="text-amber-400">○</span>
  : <span className="text-red-400">✕</span>;

export default function DashboardPage() {
  const [activePeriod, setActivePeriod] = useState<string>('1M');

  const stats = [
    { label: 'NAV', value: idr(PORTFOLIO.nav) },
    { label: 'Day P&L', value: `+${idr(PORTFOLIO.dayPnl)}`, delta: `+${PORTFOLIO.dayPnlPct}%`, positive: true },
    { label: 'Total Return', value: `+${PORTFOLIO.totalReturn}%`, delta: null, positive: true },
    { label: 'Sharpe', value: PORTFOLIO.sharpe.toFixed(2) },
    { label: 'Win Rate', value: `${PORTFOLIO.winRate}%` },
    { label: 'Open Positions', value: String(PORTFOLIO.openPositions) },
  ];

  return (
    <div className="p-4 space-y-3">
      <h1 className="terminal-page-title">Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg bg-[#111113] border border-[#1e1e22] p-3">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value text-lg">{s.value}</div>
            {s.delta && (
              <div className={`text-xs mt-0.5 ${s.positive ? 'text-emerald-400' : 'text-red-400'}`}>{s.delta}</div>
            )}
          </div>
        ))}
      </div>

      {/* Equity Curve + Strategy Status */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        {/* Equity Curve */}
        <div className="lg:col-span-3 rounded-lg bg-[#111113] border border-[#1e1e22] p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="terminal-heading mb-2">Equity Curve</span>
            <div className="flex gap-1">
              {periods.map((p) => (
                <button key={p} onClick={() => setActivePeriod(p)}
                  className={`rounded px-2 py-0.5 text-[10px] font-mono ${activePeriod === p ? 'bg-blue-600/20 text-blue-400' : 'text-white/30 hover:text-white/50'}`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.25)' }} tickLine={false} axisLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#111113', border: '1px solid #1e1e22', fontSize: 11 }}
                  labelStyle={{ color: 'rgba(255,255,255,0.4)' }} itemStyle={{ color: '#fff' }} />
                <Area type="monotone" dataKey="benchmark" stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" fill="none" dot={false} />
                <Area type="monotone" dataKey="equity" stroke="#2563eb" fill="#2563eb" fillOpacity={0.1} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Strategy Status */}
        <div className="lg:col-span-2 rounded-lg bg-[#111113] border border-[#1e1e22] p-3">
          <span className="terminal-heading mb-2">Strategies</span>
          <div className="mt-2 space-y-0">
            {STRATEGIES.map((s) => (
              <Link key={s.id} href={`/strategies/${s.id}`}
                className="flex items-center justify-between py-1.5 px-1 hover:bg-white/[0.02] rounded">
                <div className="flex items-center gap-2 text-sm text-white/70">
                  {statusIcon(s.status)}
                  <span className="font-mono text-xs">{s.name}</span>
                </div>
                <span className={`font-mono text-xs ${s.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {s.pnl >= 0 ? '+' : ''}{s.pnl.toFixed(1)}%
                </span>
              </Link>
            ))}
          </div>
          <Link href="/strategies" className="block mt-2 text-[10px] text-white/30 hover:text-white/50">View all &rarr;</Link>
        </div>
      </div>

      {/* Positions + Recent Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-[55%_1fr] gap-3">
        {/* Positions Table */}
        <div className="rounded-lg bg-[#111113] border border-[#1e1e22] p-3 overflow-x-auto">
          <span className="terminal-heading mb-2">Positions</span>
          <table className="w-full mt-2">
            <thead>
              <tr>
                <th className="table-header text-left py-1 px-3">SYM</th>
                <th className="table-header text-right py-1 px-3">QTY</th>
                <th className="table-header text-right py-1 px-3">AVG</th>
                <th className="table-header text-right py-1 px-3">CUR</th>
                <th className="table-header text-right py-1 px-3">P&L</th>
                <th className="table-header text-right py-1 px-3">P&L%</th>
              </tr>
            </thead>
            <tbody>
              {POSITIONS.map((p) => {
                const pnl = (p.currentPrice - p.avgPrice) * p.qty;
                const pnlPct = (p.currentPrice / p.avgPrice - 1) * 100;
                const pos = pnl >= 0;
                return (
                  <tr key={p.symbol} className="border-b border-[#1e1e22] hover:bg-white/[0.02] cursor-pointer"
                    onClick={() => window.location.href = `/markets/${p.symbol}`}>
                    <td className="py-2 px-3 font-mono text-sm text-white">{p.symbol}</td>
                    <td className="py-2 px-3 font-mono text-sm text-white/70 text-right">{p.qty.toLocaleString('id-ID')}</td>
                    <td className="py-2 px-3 font-mono text-sm text-white/70 text-right">{new Intl.NumberFormat('id-ID').format(p.avgPrice)}</td>
                    <td className="py-2 px-3 font-mono text-sm text-white/70 text-right">{new Intl.NumberFormat('id-ID').format(p.currentPrice)}</td>
                    <td className={`py-2 px-3 font-mono text-sm text-right ${pos ? 'text-emerald-400' : 'text-red-400'}`}>
                      {pos ? '+' : ''}{idr(pnl)}
                    </td>
                    <td className={`py-2 px-3 font-mono text-sm text-right ${pos ? 'text-emerald-400' : 'text-red-400'}`}>
                      {pos ? '+' : ''}{pnlPct.toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <Link href="/portfolio/positions" className="block mt-2 text-[10px] text-white/30 hover:text-white/50">View all &rarr;</Link>
        </div>

        {/* Recent Orders */}
        <div className="rounded-lg bg-[#111113] border border-[#1e1e22] p-3 overflow-x-auto">
          <span className="terminal-heading mb-2">Recent Orders</span>
          <table className="w-full mt-2">
            <thead>
              <tr>
                <th className="table-header text-left py-1 px-3">TIME</th>
                <th className="table-header text-left py-1 px-3">SIDE</th>
                <th className="table-header text-left py-1 px-3">SYM</th>
                <th className="table-header text-right py-1 px-3">QTY</th>
                <th className="table-header text-left py-1 px-3">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {RECENT_ORDERS.map((o) => (
                <tr key={o.id} className="border-b border-[#1e1e22] hover:bg-white/[0.02]">
                  <td className="py-2 px-3 font-mono text-xs text-white/30">{o.time}</td>
                  <td className={`py-2 px-3 font-mono text-sm ${o.side === 'BUY' ? 'text-blue-400' : 'text-red-400'}`}>{o.side}</td>
                  <td className="py-2 px-3 font-mono text-sm text-white">{o.symbol}</td>
                  <td className="py-2 px-3 font-mono text-sm text-white/70 text-right">{o.qty.toLocaleString('id-ID')}</td>
                  <td className="py-2 px-3 text-sm">
                    {o.status === 'filled'
                      ? <span className="text-emerald-400">●</span>
                      : <span className="text-amber-400">◐</span>}
                    <span className="ml-1.5 text-white/50 text-xs">{o.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Link href="/portfolio/orders" className="block mt-2 text-[10px] text-white/30 hover:text-white/50">View all &rarr;</Link>
        </div>
      </div>

      <TerminalDisclaimer />
    </div>
  );
}
