'use client';

import { useState, useMemo } from 'react';
import { PORTFOLIO, POSITIONS, RECENT_ORDERS, MONTHLY_RETURNS } from '@/mocks/terminal-data';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';

const TABS = ['Overview', 'Positions', 'Orders', 'Risk', 'Performance'] as const;
type Tab = (typeof TABS)[number];

function fmt(n: number, decimals = 0) {
  return n.toLocaleString('en-US', { maximumFractionDigits: decimals });
}
function fmtB(n: number) {
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  return fmt(n);
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-[#1e1e22] bg-white/[0.02] p-3">
      <div className="text-[10px] uppercase tracking-wider text-white/30">{label}</div>
      <div className={`mt-1 font-mono text-lg font-semibold ${color ?? 'text-white/90'}`}>{value}</div>
    </div>
  );
}

function TH({ children, mono }: { children: React.ReactNode; mono?: boolean }) {
  return (
    <th className={`px-3 py-2 text-left text-[10px] uppercase tracking-wider text-white/30 ${mono ? 'font-mono' : ''}`}>
      {children}
    </th>
  );
}

// ── Overview ──
function OverviewTab() {
  const sectorWeights = useMemo(() => {
    const map: Record<string, number> = {};
    POSITIONS.forEach((p) => { map[p.sector] = (map[p.sector] ?? 0) + p.weight; });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, []);
  const maxWeight = sectorWeights[0]?.[1] ?? 1;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <StatCard label="NAV" value={fmtB(PORTFOLIO.nav)} />
        <StatCard label="Day P&L" value={`+${fmtB(PORTFOLIO.dayPnl)}`} color="text-emerald-400" />
        <StatCard label="Invested" value={fmtB(PORTFOLIO.invested)} />
        <StatCard label="Cash" value={fmtB(PORTFOLIO.cash)} />
      </div>
      <div className="rounded-lg border border-[#1e1e22] bg-white/[0.02] p-3">
        <div className="mb-2 text-[10px] uppercase tracking-wider text-white/30">Sector Exposure</div>
        <div className="flex flex-col gap-1.5">
          {sectorWeights.map(([sector, weight]) => (
            <div key={sector} className="flex items-center gap-2">
              <span className="w-20 shrink-0 text-xs text-white/50">{sector}</span>
              <div className="h-4 flex-1 rounded bg-white/[0.04]">
                <div
                  className="h-full rounded bg-blue-500/30"
                  style={{ width: `${(weight / maxWeight) * 100}%` }}
                />
              </div>
              <span className="w-12 shrink-0 text-right font-mono text-xs text-white/60">{weight.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Positions ──
function PositionsTab() {
  const rows = POSITIONS.map((p) => {
    const pnl = (p.currentPrice - p.avgPrice) * p.qty;
    const pnlPct = ((p.currentPrice - p.avgPrice) / p.avgPrice) * 100;
    return { ...p, pnl, pnlPct };
  });
  const totalPnl = rows.reduce((s, r) => s + r.pnl, 0);

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1e1e22]">
      <table className="w-full text-xs text-white/70">
        <thead className="border-b border-[#1e1e22] bg-white/[0.02]">
          <tr>
            <TH>Symbol</TH><TH>Name</TH><TH>Qty</TH><TH>Lots</TH>
            <TH>Avg</TH><TH>Current</TH><TH>P&L</TH><TH>P&L%</TH><TH>Weight</TH>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.symbol} className="border-b border-[#1e1e22] hover:bg-white/[0.02]">
              <td className="px-3 py-2.5 font-medium text-white/90">{r.symbol}</td>
              <td className="px-3 py-2.5 text-white/40">{r.name}</td>
              <td className="px-3 py-2.5 font-mono">{fmt(r.qty)}</td>
              <td className="px-3 py-2.5 font-mono">{r.lots}</td>
              <td className="px-3 py-2.5 font-mono">{fmt(r.avgPrice)}</td>
              <td className="px-3 py-2.5 font-mono">{fmt(r.currentPrice)}</td>
              <td className={`px-3 py-2.5 font-mono ${r.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {r.pnl >= 0 ? '+' : ''}{fmt(r.pnl)}
              </td>
              <td className={`px-3 py-2.5 font-mono ${r.pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {r.pnlPct >= 0 ? '+' : ''}{r.pnlPct.toFixed(2)}%
              </td>
              <td className="px-3 py-2.5 font-mono">{r.weight}%</td>
            </tr>
          ))}
          <tr className="border-t border-white/10 bg-white/[0.03]">
            <td className="px-3 py-2.5 font-medium text-white/60" colSpan={6}>Total</td>
            <td className={`px-3 py-2.5 font-mono font-semibold ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalPnl >= 0 ? '+' : ''}{fmt(totalPnl)}
            </td>
            <td colSpan={2} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ── Orders ──
function OrdersTab() {
  return (
    <div className="overflow-x-auto rounded-lg border border-[#1e1e22]">
      <table className="w-full text-xs text-white/70">
        <thead className="border-b border-[#1e1e22] bg-white/[0.02]">
          <tr><TH>ID</TH><TH>Time</TH><TH>Side</TH><TH>Symbol</TH><TH>Qty</TH><TH>Price</TH><TH>Status</TH></tr>
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Risk ──
const CORR_SYMBOLS = ['BBCA', 'BMRI', 'TLKM', 'ASII'];
const CORR_MATRIX = [
  [1.0, 0.82, 0.35, 0.41],
  [0.82, 1.0, 0.28, 0.38],
  [0.35, 0.28, 1.0, 0.52],
  [0.41, 0.38, 0.52, 1.0],
];

function RiskTab() {
  const riskStats = [
    { label: 'VaR 95%', value: `${PORTFOLIO.var95}%` },
    { label: 'CVaR', value: `${PORTFOLIO.cvar95}%` },
    { label: 'Max DD', value: `${PORTFOLIO.maxDrawdown}%` },
    { label: 'Beta', value: `${PORTFOLIO.beta}` },
    { label: 'Tracking Err', value: `${PORTFOLIO.trackingError}` },
    { label: 'Info Ratio', value: `${PORTFOLIO.infoRatio}` },
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-3 gap-2 lg:grid-cols-6">
        {riskStats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} />
        ))}
      </div>
      <div className="rounded-lg border border-[#1e1e22] bg-white/[0.02] p-3">
        <div className="mb-2 text-[10px] uppercase tracking-wider text-white/30">Correlation Matrix</div>
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="px-2 py-1" />
              {CORR_SYMBOLS.map((s) => (
                <th key={s} className="px-2 py-1 text-center font-mono text-white/40">{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CORR_MATRIX.map((row, i) => (
              <tr key={CORR_SYMBOLS[i]}>
                <td className="px-2 py-1 font-mono text-white/40">{CORR_SYMBOLS[i]}</td>
                {row.map((val, j) => {
                  const opacity = Math.round(val * 40 + 5);
                  return (
                    <td
                      key={j}
                      className="px-2 py-1 text-center font-mono text-white/70"
                      style={{ backgroundColor: `rgba(59, 130, 246, ${opacity / 100})` }}
                    >
                      {val.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Performance ──
function PerformanceTab() {
  return (
    <div className="overflow-x-auto rounded-lg border border-[#1e1e22]">
      <table className="w-full text-xs text-white/70">
        <thead className="border-b border-[#1e1e22] bg-white/[0.02]">
          <tr><TH>Month</TH><TH>Portfolio</TH><TH>Benchmark</TH><TH>Alpha</TH></tr>
        </thead>
        <tbody>
          {MONTHLY_RETURNS.map((m) => {
            const alpha = +(m.portfolio - m.benchmark).toFixed(1);
            const cell = (v: number) => (
              <td className={`px-3 py-2.5 font-mono ${
                v >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
              }`}>
                {v >= 0 ? '+' : ''}{v.toFixed(1)}%
              </td>
            );
            return (
              <tr key={m.month} className="border-b border-[#1e1e22]">
                <td className="px-3 py-2.5 text-white/60">{m.month}</td>
                {cell(m.portfolio)}
                {cell(m.benchmark)}
                {cell(alpha)}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main ──
export default function PortfolioPage() {
  const [tab, setTab] = useState<Tab>('Overview');

  return (
    <div className="flex min-h-full flex-col gap-3 p-4">
      <h1 className="text-sm font-semibold text-white/90">Portfolio</h1>

      <div className="flex gap-1 border-b border-[#1e1e22]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-xs transition-colors ${
              tab === t
                ? 'border-b-2 border-white/60 text-white/80'
                : 'text-white/30 hover:text-white/50'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && <OverviewTab />}
      {tab === 'Positions' && <PositionsTab />}
      {tab === 'Orders' && <OrdersTab />}
      {tab === 'Risk' && <RiskTab />}
      {tab === 'Performance' && <PerformanceTab />}

      <TerminalDisclaimer />
    </div>
  );
}
