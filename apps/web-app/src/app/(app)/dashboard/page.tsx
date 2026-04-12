'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts';
import {
  PORTFOLIO, POSITIONS, INDICES, SECTORS, MARKET_BREADTH,
  MONTHLY_RETURNS, generateEquityCurve,
} from '@/mocks/terminal-data';

const idr = (v: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(v);
const pct = (v: number, dec = 2) => `${v >= 0 ? '+' : ''}${v.toFixed(dec)}%`;
const equityData = generateEquityCurve(90);

const RISK_SOURCES = [
  { source: 'Market', risk: 8.42, contribution: 59.2 },
  { source: 'Local Events', risk: 3.05, contribution: 21.5 },
  { source: 'Sectors', risk: 1.84, contribution: 12.9 },
  { source: 'IDX Indices', risk: 0.62, contribution: 4.4 },
  { source: 'Currency', risk: 0.21, contribution: 1.5 },
  { source: 'Specific', risk: 0.08, contribution: 0.5 },
];

const FACTOR_RISK = [
  { factor: 'Value', exposure: 0.42, contribution: 1.8 },
  { factor: 'Momentum', exposure: 0.85, contribution: 3.2 },
  { factor: 'Quality', exposure: 0.31, contribution: 0.9 },
  { factor: 'Size', exposure: -0.22, contribution: -0.5 },
  { factor: 'Volatility', exposure: -0.65, contribution: -2.1 },
  { factor: 'Liquidity', exposure: 0.18, contribution: 0.4 },
  { factor: 'Dividend', exposure: 0.55, contribution: 1.2 },
  { factor: 'Growth', exposure: 0.12, contribution: 0.3 },
];

const tabs = ['Portfolio Summary', 'Equity Factor Risk', 'Risk Trend', 'Asset'] as const;

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-4 py-3">
      <span className="text-[10px] font-medium uppercase tracking-wider text-white/35">{label}</span>
      <span className="text-[20px] font-semibold tabular-nums text-white">{value}</span>
      {sub && <span className="text-[11px] text-white/40">{sub}</span>}
    </div>
  );
}

function SectionHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-[13px] font-semibold text-white/80">{title}</h3>
      {children}
    </div>
  );
}

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-white/[0.06] bg-[#0d1117] p-4 ${className}`}>
      {children}
    </div>
  );
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<string>('Equity Factor Risk');
  const [riskPeriod, setRiskPeriod] = useState('3 Months');

  const topAssets = POSITIONS.slice().sort((a, b) => b.weight - a.weight);
  const totalRisk = RISK_SOURCES.reduce((s, r) => s + r.risk, 0);

  return (
    <div className="min-h-full bg-[#0a0e14] p-4">
      {/* Portfolio Header */}
      <div className="mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-[18px] font-semibold text-white">PYHRON IDX QUALITY - Daily</h1>
          <span className="rounded bg-white/[0.06] px-2 py-0.5 text-[10px] text-white/40">Equity Factor Risk</span>
        </div>
        <div className="mt-1 flex items-center gap-4 text-[11px] text-white/35">
          <span>Portfolio: <strong className="text-white/60">IDX Quality</strong></span>
          <span>Benchmark: <strong className="text-white/60">IHSG</strong></span>
          <span>As of date: <strong className="text-white/60">11 Apr 2026</strong></span>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-0 border-b border-white/[0.06]">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`border-b-2 px-4 py-2.5 text-[12px] font-medium transition-colors ${
              activeTab === t
                ? 'border-[#2563eb] text-white'
                : 'border-transparent text-white/40 hover:text-white/60'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Key Metrics Row — MSCI One style */}
      <div className="mb-4 flex flex-wrap items-stretch divide-x divide-white/[0.06] rounded-lg border border-white/[0.06] bg-[#0d1117]">
        <MetricCard label="Market Value" value={`${(PORTFOLIO.nav / 1e9).toFixed(2)}B`} sub="IDR" />
        <MetricCard label="Active Risk" value={`${(totalRisk * 0.27).toFixed(2)}%`} />
        <MetricCard label="Total Risk" value={`${totalRisk.toFixed(2)}%`} />
        <MetricCard label="Beta" value={PORTFOLIO.beta.toFixed(2)} />
        <MetricCard label="Weight Top 10" value={`${topAssets.slice(0, 10).reduce((s, a) => s + a.weight, 0).toFixed(2)}%`} />
        <MetricCard label="Active Risk Top 10" value={`${(totalRisk * 0.48).toFixed(2)}%`} />
        <MetricCard label="No. of Assets" value={String(POSITIONS.length)} sub="Active" />
      </div>

      {/* Main Grid — 2 columns */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {/* Risk Decomposition Table */}
        <Panel>
          <SectionHeader title="Risk Decomposition" />
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="pb-2 text-left text-[10px] font-medium uppercase tracking-wider text-white/30">Risk Source</th>
                <th className="pb-2 text-right text-[10px] font-medium uppercase tracking-wider text-white/30">Risk %</th>
                <th className="pb-2 text-right text-[10px] font-medium uppercase tracking-wider text-white/30">Contribution %</th>
                <th className="pb-2 text-right text-[10px] font-medium uppercase tracking-wider text-white/30">Bar</th>
              </tr>
            </thead>
            <tbody>
              {RISK_SOURCES.map((r) => (
                <tr key={r.source} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                  <td className="py-2 text-[12px] text-white/70">{r.source}</td>
                  <td className="py-2 text-right font-mono text-[12px] text-white/60">{r.risk.toFixed(2)}%</td>
                  <td className="py-2 text-right font-mono text-[12px] text-white/60">{r.contribution.toFixed(1)}%</td>
                  <td className="py-2 text-right">
                    <div className="ml-auto h-2 w-24 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className="h-full rounded-full bg-[#2563eb]" style={{ width: `${r.contribution}%` }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Local Market Risk Breakdown */}
        <Panel>
          <SectionHeader title="Local Market Risk Breakdown">
            <div className="flex gap-3 text-[10px] text-white/30">
              <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-[#2563eb]" /> Portfolio</span>
              <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-[#06b6d4]" /> Benchmark</span>
            </div>
          </SectionHeader>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={SECTORS.map((s) => ({ name: s.name, portfolio: s.weight, benchmark: s.weight * 0.85 + 2 }))}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.25)' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.08)', fontSize: 11, borderRadius: 6 }} />
                <Bar dataKey="portfolio" fill="#2563eb" radius={[2, 2, 0, 0]} barSize={14} />
                <Bar dataKey="benchmark" fill="#06b6d4" radius={[2, 2, 0, 0]} barSize={14} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Risk Trend */}
        <Panel>
          <SectionHeader title="Risk Trend">
            <div className="flex gap-1">
              {['1 Month', '3 Months', '1 Year'].map((p) => (
                <button key={p} onClick={() => setRiskPeriod(p)}
                  className={`rounded px-2.5 py-1 text-[10px] ${riskPeriod === p ? 'bg-[#2563eb]/20 text-[#60a5fa]' : 'text-white/30 hover:text-white/50'}`}>
                  {p}
                </button>
              ))}
            </div>
          </SectionHeader>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData.slice(-60)}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.25)' }} tickLine={false} axisLine={false} tickFormatter={(v) => v.slice(5)} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.08)', fontSize: 11, borderRadius: 6 }} />
                <Area type="monotone" dataKey="equity" stroke="#2563eb" fill="#2563eb" fillOpacity={0.08} strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Factor Risk Contribution */}
        <Panel>
          <SectionHeader title="Top Factors by Risk Contribution" />
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={FACTOR_RISK.sort((a, b) => b.contribution - a.contribution)} layout="vertical">
                <CartesianGrid stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.25)' }} tickLine={false} axisLine={false} />
                <YAxis dataKey="factor" type="category" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} tickLine={false} axisLine={false} width={80} />
                <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.08)', fontSize: 11, borderRadius: 6 }} />
                <Bar dataKey="contribution" radius={[0, 3, 3, 0]} barSize={16}>
                  {FACTOR_RISK.sort((a, b) => b.contribution - a.contribution).map((f, i) => (
                    <Cell key={i} fill={f.contribution >= 0 ? '#2563eb' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      {/* Bottom Row — Asset Tables */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        {/* Top 10 Assets by Weight */}
        <Panel>
          <SectionHeader title="Top 10 Assets by Weight" />
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="pb-2 text-left text-[10px] font-medium uppercase tracking-wider text-white/30">Asset Name</th>
                <th className="pb-2 text-right text-[10px] font-medium uppercase tracking-wider text-white/30">Weight</th>
                <th className="pb-2 text-right text-[10px] font-medium uppercase tracking-wider text-white/30">Risk Cont.</th>
              </tr>
            </thead>
            <tbody>
              {topAssets.map((a) => (
                <tr key={a.symbol} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                  <td className="py-2">
                    <div className="text-[12px] text-white/80">{a.name}</div>
                    <div className="text-[10px] text-white/30">{a.symbol} / {a.sector}</div>
                  </td>
                  <td className="py-2 text-right font-mono text-[12px] text-white/60">{a.weight.toFixed(1)}%</td>
                  <td className="py-2 text-right font-mono text-[12px] text-white/60">{(a.weight * 0.35).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Monthly Performance */}
        <Panel>
          <SectionHeader title="Monthly Performance Attribution">
            <div className="flex gap-3 text-[10px] text-white/30">
              <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-[#2563eb]" /> Portfolio</span>
              <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-white/20" /> Benchmark</span>
            </div>
          </SectionHeader>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MONTHLY_RETURNS}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.25)' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.08)', fontSize: 11, borderRadius: 6 }} />
                <Bar dataKey="portfolio" fill="#2563eb" radius={[2, 2, 0, 0]} barSize={14} />
                <Bar dataKey="benchmark" fill="rgba(255,255,255,0.15)" radius={[2, 2, 0, 0]} barSize={14} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      {/* Footer */}
      <div className="mt-6 border-t border-white/[0.06] pt-4 text-center text-[10px] text-white/20">
        &copy; {new Date().getFullYear()} Pyhron. All Rights Reserved. Subject to{' '}
        <Link href="/legal/terms" className="underline hover:text-white/40">Terms of Use</Link> &{' '}
        <Link href="/legal/disclaimer" className="underline hover:text-white/40">Disclaimer</Link>.
      </div>
    </div>
  );
}
