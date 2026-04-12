'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import {
  PORTFOLIO, POSITIONS, SECTORS, MONTHLY_RETURNS, generateEquityCurve,
} from '@/mocks/terminal-data';

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
    <div className="flex flex-col gap-1 border-r border-[#e5e7eb] px-6 py-4 last:border-r-0">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-[#6b7280]">{label}</span>
      <span className="text-[24px] font-semibold leading-none text-[#111827]">{value}</span>
      {sub && <span className="text-[11px] text-[#9ca3af]">{sub}</span>}
    </div>
  );
}

function Panel({ title, children, headerRight }: { title: string; children: React.ReactNode; headerRight?: React.ReactNode }) {
  return (
    <div className="rounded-md border border-[#e5e7eb] bg-white">
      <div className="flex items-center justify-between border-b border-[#e5e7eb] px-5 py-3">
        <h3 className="text-[14px] font-semibold text-[#111827]">{title}</h3>
        {headerRight}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<string>('Equity Factor Risk');
  const [riskPeriod, setRiskPeriod] = useState('3 Months');

  const topAssets = [...POSITIONS].sort((a, b) => b.weight - a.weight);
  const totalRisk = RISK_SOURCES.reduce((s, r) => s + r.risk, 0);
  const sortedFactors = [...FACTOR_RISK].sort((a, b) => b.contribution - a.contribution);

  return (
    <div className="min-h-full bg-[#f3f4f6] p-6">
      {/* Portfolio Header */}
      <div className="mb-5">
        <div className="flex items-center gap-3">
          <h1 className="text-[20px] font-bold text-[#111827]">PYHRON IDX QUALITY - Daily</h1>
          <span className="rounded border border-[#d1d5db] bg-[#f9fafb] px-2.5 py-0.5 text-[11px] font-medium text-[#6b7280]">Equity Factor Risk</span>
        </div>
        <div className="mt-2 flex items-center gap-5 text-[12px] text-[#6b7280]">
          <span>Portfolio: <strong className="font-semibold text-[#374151]">IDX Quality</strong></span>
          <span>Benchmark: <strong className="font-semibold text-[#374151]">IHSG</strong></span>
          <span>As of date: <strong className="font-semibold text-[#374151]">11 Apr 2026</strong></span>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-5 flex gap-0 border-b border-[#e5e7eb]">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`border-b-2 px-5 py-3 text-[13px] font-medium transition-colors ${
              activeTab === t
                ? 'border-[#2563eb] text-[#2563eb]'
                : 'border-transparent text-[#6b7280] hover:text-[#374151]'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Key Metrics Row */}
      <div className="mb-5 flex flex-wrap items-stretch rounded-md border border-[#e5e7eb] bg-white">
        <MetricCard label="Market Value" value={`${(PORTFOLIO.nav / 1e9).toFixed(2)}B`} sub="IDR" />
        <MetricCard label="Active Risk" value={`${(totalRisk * 0.27).toFixed(2)}%`} />
        <MetricCard label="Total Risk" value={`${totalRisk.toFixed(2)}%`} />
        <MetricCard label="Beta" value={PORTFOLIO.beta.toFixed(2)} />
        <MetricCard label="Weight Top 10" value={`${topAssets.slice(0, 10).reduce((s, a) => s + a.weight, 0).toFixed(2)}%`} />
        <MetricCard label="Active Risk Top 10" value={`${(totalRisk * 0.48).toFixed(2)}%`} />
        <MetricCard label="No. of Assets" value={String(POSITIONS.length)} sub="Active" />
      </div>

      {/* Main Grid — 2 columns */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        {/* Risk Decomposition */}
        <Panel title="Risk Decomposition">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#e5e7eb]">
                <th className="pb-3 text-left text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Risk Source</th>
                <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Risk %</th>
                <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Contribution %</th>
                <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Bar</th>
              </tr>
            </thead>
            <tbody>
              {RISK_SOURCES.map((r) => (
                <tr key={r.source} className="border-b border-[#f3f4f6]">
                  <td className="py-3 text-[13px] font-medium text-[#374151]">{r.source}</td>
                  <td className="py-3 text-right font-mono text-[13px] text-[#6b7280]">{r.risk.toFixed(2)}%</td>
                  <td className="py-3 text-right font-mono text-[13px] text-[#6b7280]">{r.contribution.toFixed(1)}%</td>
                  <td className="py-3">
                    <div className="ml-auto flex h-2 w-28 items-center">
                      <div className="h-full rounded-full bg-[#2563eb]" style={{ width: `${r.contribution}%` }} />
                      <div className="h-full flex-1 rounded-full bg-[#e5e7eb]" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Local Market Risk Breakdown */}
        <Panel
          title="Local Market Risk Breakdown"
          headerRight={
            <div className="flex gap-4 text-[11px] text-[#9ca3af]">
              <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2563eb]" /> Portfolio</span>
              <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#06b6d4]" /> Benchmark</span>
            </div>
          }
        >
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={SECTORS.map((s) => ({ name: s.name, portfolio: s.weight, benchmark: s.weight * 0.85 + 2 }))}>
                <CartesianGrid stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', fontSize: 12, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
                <Bar dataKey="portfolio" fill="#2563eb" radius={[2, 2, 0, 0]} barSize={16} />
                <Bar dataKey="benchmark" fill="#06b6d4" radius={[2, 2, 0, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Risk Trend */}
        <Panel
          title="Risk Trend"
          headerRight={
            <div className="flex gap-1">
              {['1 Month', '3 Months', '1 Year'].map((p) => (
                <button key={p} onClick={() => setRiskPeriod(p)}
                  className={`rounded px-3 py-1 text-[11px] font-medium ${riskPeriod === p ? 'bg-[#2563eb] text-white' : 'bg-[#f3f4f6] text-[#6b7280] hover:bg-[#e5e7eb]'}`}>
                  {p}
                </button>
              ))}
            </div>
          }
        >
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData.slice(-60)}>
                <CartesianGrid stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', fontSize: 12, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
                <Area type="monotone" dataKey="equity" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.08} strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Top Factors by Risk Contribution */}
        <Panel title="Top Factors by Risk Contribution">
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sortedFactors} layout="vertical">
                <CartesianGrid stroke="#f3f4f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
                <YAxis dataKey="factor" type="category" tick={{ fontSize: 12, fill: '#374151' }} tickLine={false} axisLine={false} width={80} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', fontSize: 12, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
                <Bar dataKey="contribution" radius={[0, 3, 3, 0]} barSize={18}>
                  {sortedFactors.map((f, i) => (
                    <Cell key={i} fill={f.contribution >= 0 ? '#2563eb' : '#f97316'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      {/* Bottom Row */}
      <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1fr]">
        {/* Top 10 Assets by Weight */}
        <Panel title="Top 10 Assets by Weight">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#e5e7eb]">
                <th className="pb-3 text-left text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Asset Name</th>
                <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Weight</th>
                <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wide text-[#9ca3af]">Risk Contribution</th>
              </tr>
            </thead>
            <tbody>
              {topAssets.map((a) => (
                <tr key={a.symbol} className="border-b border-[#f3f4f6]">
                  <td className="py-2.5">
                    <div className="text-[13px] font-medium text-[#111827]">{a.name}</div>
                    <div className="text-[11px] text-[#9ca3af]">{a.symbol}</div>
                  </td>
                  <td className="py-2.5 text-right font-mono text-[13px] text-[#374151]">{a.weight.toFixed(1)}%</td>
                  <td className="py-2.5 text-right font-mono text-[13px] text-[#374151]">{(a.weight * 0.35).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Top 15 Assets by Risk Contribution */}
        <Panel
          title="Monthly Performance"
          headerRight={
            <div className="flex gap-4 text-[11px] text-[#9ca3af]">
              <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2563eb]" /> Portfolio</span>
              <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#d1d5db]" /> Benchmark</span>
            </div>
          }
        >
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MONTHLY_RETURNS}>
                <CartesianGrid stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', fontSize: 12, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
                <Bar dataKey="portfolio" fill="#2563eb" radius={[2, 2, 0, 0]} barSize={16} />
                <Bar dataKey="benchmark" fill="#d1d5db" radius={[2, 2, 0, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      {/* Footer */}
      <div className="mt-6 border-t border-[#e5e7eb] pt-4 text-center text-[11px] text-[#9ca3af]">
        &copy; {new Date().getFullYear()} Pyhron. All Rights Reserved. Subject to{' '}
        <Link href="/legal/terms" className="underline hover:text-[#6b7280]">Terms of Use</Link> &{' '}
        <Link href="/legal/disclaimer" className="underline hover:text-[#6b7280]">Disclaimer</Link>.
      </div>
    </div>
  );
}
