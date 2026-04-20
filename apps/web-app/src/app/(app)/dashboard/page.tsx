'use client';

import Link from 'next/link';
import { Building2, LineChart, BarChart3 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';

const card = 'rounded-[15px] border border-[#e2e8f0] bg-white';

function isIDXOpen(): boolean {
  const now = new Date();
  const h = (now.getUTCHours() + 7) % 24;
  const m = now.getUTCMinutes();
  const d = now.getDay();
  if (d === 0 || d === 6) return false;
  const t = h * 60 + m;
  return (t >= 540 && t <= 690) || (t >= 810 && t <= 910);
}

function useIdx(symbol: string) {
  return useQuery<{
    symbol: string;
    current: number;
    open: number;
    change: number;
    points: number[];
    timestamps: string[];
    lastUpdate: string;
  }>({
    queryKey: ['intraday', symbol],
    queryFn: async () => {
      const r = await fetch(`/api/v1/markets/intraday/${encodeURIComponent(symbol)}`);
      if (!r.ok) throw new Error('fetch failed');
      return r.json();
    },
    refetchInterval: isIDXOpen() ? 30_000 : false,
    staleTime: 15_000,
    enabled: !!symbol,
  });
}

type EconEvent = { date: string; indicator: string; unit: string; previous: string; forecast: string; current: string; released: boolean };

function useEconCalendar() {
  return useQuery<EconEvent[]>({
    queryKey: ['econ-calendar'],
    queryFn: async () => {
      const r = await fetch('/api/v1/markets/economic-calendar');
      if (!r.ok) throw new Error('fetch failed');
      return r.json();
    },
    staleTime: 3600_000,
  });
}

function fmtNum(v: string): string {
  if (!v || v === '\u2014' || v === '-') return '\u2014';
  if (/[A-Za-z]/.test(v)) return v;
  const n = parseFloat(v.replace(/,/g, ''));
  if (isNaN(n)) return v;
  if (Math.abs(n) >= 10000) return n.toLocaleString('en-US', { maximumFractionDigits: 0 });
  if (Math.abs(n) >= 100) return n.toFixed(1);
  return n.toFixed(2);
}

function IndexSparkline({ pts, symbol, changePercent }: { pts: number[]; symbol: string; changePercent: number }) {
  if (pts.length < 2) return <div className="h-11 w-full" />;
  const isPositive = changePercent >= 0;
  const strokeColor = isPositive ? '#00875A' : '#D92D20';
  const gradientId = `spark-gradient-${symbol.replace(/[^a-zA-Z0-9]/g, '-')}`;
  const data = pts.map((value) => ({ value }));
  return (
    <ResponsiveContainer width="100%" height={44}>
      <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={strokeColor} stopOpacity={0.18} />
            <stop offset="95%" stopColor={strokeColor} stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="value"
          stroke={strokeColor}
          strokeWidth={1.5}
          fill={`url(#${gradientId})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

const IDX_FALLBACK: Record<string, { base: number; change: number }> = {
  IHSG: { base: 7234.56, change: 0.45 },
  LQ45: { base: 985.23, change: -0.52 },
  IDX30: { base: 482.18, change: 0.58 },
  IDX80: { base: 132.45, change: 0.66 },
  JII: { base: 548.92, change: -0.58 },
};

function seeded(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function fallbackPts(symbol: string): number[] {
  const fb = IDX_FALLBACK[symbol] ?? { base: 500, change: 0 };
  const n = 200;
  const open = fb.base / (1 + fb.change / 100);
  const target = fb.base;
  const rand = seeded(symbol.split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 97);
  const vol = fb.base * 0.003;
  const pts: number[] = [];
  let price = open;
  let trend = 0;
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const expected = open + (target - open) * t;
    const meanRev = (expected - price) * 0.015;
    trend = trend * 0.93 + (rand() - 0.5) * vol * 0.35;
    const noise = (rand() - 0.5) * vol;
    const jump = rand() > 0.97 ? (rand() - 0.5) * vol * 3 : 0;
    price += meanRev + trend + noise + jump;
    pts.push(Math.round(price * 100) / 100);
  }
  pts[n - 1] = target;
  return pts;
}

function nowJakarta(): string {
  return new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Jakarta',
  });
}

function IdxCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useIdx(symbol);
  const fb = IDX_FALLBACK[symbol] ?? { base: 0, change: 0 };
  const cur = data?.current && data.current > 0 ? data.current : fb.base;
  const chg = data?.change ?? fb.change;
  const apiPts = data?.points ?? [];
  const pts = apiPts.length >= 2 ? apiPts : fallbackPts(symbol);
  const ts = data?.lastUpdate || (isLoading ? '--:--' : nowJakarta());
  const up = chg >= 0;

  return (
    <div
      className="flex flex-col justify-between overflow-hidden"
      style={{
        background: 'var(--color-bg-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        padding: 16,
        minHeight: 120,
      }}
    >
      <div className="flex items-center justify-between">
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--color-text-muted)',
          }}
        >
          {symbol}
        </span>
        <span className="tabular-nums" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
          {ts}
        </span>
      </div>
      <div className="flex items-center" style={{ gap: 8, marginTop: 6 }}>
        <span
          className="tabular-nums"
          style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text-primary)' }}
        >
          {cur.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
        <span
          className="tabular-nums"
          style={{
            background: up ? 'var(--color-positive-bg)' : 'var(--color-negative-bg)',
            color: up ? 'var(--color-positive)' : 'var(--color-negative)',
            borderRadius: 4,
            padding: '2px 6px',
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          {up ? '\u25B2' : '\u25BC'} {up ? '+' : ''}{chg.toFixed(2)}%
        </span>
      </div>
      <div className="-mx-2 mt-auto">
        <IndexSparkline pts={pts} symbol={symbol} changePercent={chg} />
      </div>
    </div>
  );
}

// Data

const IDX_SYMBOLS = ['IHSG', 'LQ45', 'IDX30', 'IDX80', 'JII'];

const ARTICLES = [
  { id: 'prop', title: 'Latest on Indonesian Commercial-Property Pricing', desc: 'We report the latest trends in the RCA CPPI for Indonesia. We cover the all-property index and indexes for the major property types including industrial, retail, apartment and office.', gradient: 'linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%)' },
  { id: 'carbon', title: 'Carbon-Credit Integrity in the ACCU Market', desc: 'Integrity matters in compliance markets. MSCI Carbon Markets\u2019 analysis of ACCU ARR projects reveals pricing premiums, project-level risk variation and how methodology design shapes outcomes.', gradient: 'linear-gradient(135deg, #1a4a3a 0%, #2d8a6a 100%)' },
  { id: 'gap', title: 'The Transparency Gap: GP Data Rooms', desc: 'Transparency has become one of the defining challenges in the relationship between GPs and LPs in private markets. This analysis identifies where the data falls short during due diligence.', gradient: 'linear-gradient(135deg, #2d1a5c 0%, #6a2d9f 100%)' },
  { id: 'energy', title: 'Positioning Portfolios for the Energy Transition', desc: 'Do funds better positioned for the energy transition outperform? We introduce a forward-looking quadrant framework to assess transition risk and readiness \u2014 and their portfolio implications.', gradient: 'linear-gradient(135deg, #4a3000 0%, #9f7a2d 100%)' },
];

const ECON_FALLBACK: EconEvent[] = [
  { date: 'Apr 16', indicator: 'BI Rate Decision', unit: '%', previous: '5.75', forecast: '5.75', current: '5.75', released: true },
  { date: 'Apr 20', indicator: 'Trade Balance', unit: '', previous: '3.45B', forecast: '3.20B', current: '\u2014', released: false },
  { date: 'Apr 22', indicator: 'China LPR (1Y)', unit: '%', previous: '3.10', forecast: '3.10', current: '\u2014', released: false },
  { date: 'Apr 23', indicator: 'Consumer Confidence', unit: '', previous: '125.6', forecast: '126.5', current: '\u2014', released: false },
  { date: 'Apr 25', indicator: 'Foreign Reserves', unit: '', previous: '157.1B', forecast: '158.0B', current: '\u2014', released: false },
  { date: 'Apr 30', indicator: 'Fed Funds Rate', unit: '%', previous: '4.50', forecast: '4.50', current: '\u2014', released: false },
];

const ACTIONS = [
  { date: 'Apr 18', sym: 'BBCA', act: 'Cash Dividend', detail: 'IDR 180/share \u00b7 Ex: 22 Apr' },
  { date: 'Apr 22', sym: 'BMRI', act: 'Rights Issue', detail: '1:4 ratio \u00b7 Price: IDR 5,500' },
  { date: 'Apr 25', sym: '\u2014', act: 'LQ45 Rebalancing', detail: 'Effective: 25 Apr 2026' },
  { date: 'May 2', sym: 'TLKM', act: 'Cash Dividend', detail: 'IDR 95/share \u00b7 Ex: 5 May' },
  { date: 'May 15', sym: '\u2014', act: 'IDX80 Review', detail: 'Effective: 15 May 2026 (Semi-annual)' },
];

const VISITED = [
  { cat: 'Companies', label: 'Index Composition Viewer', Icon: Building2, time: 'Today' },
  { cat: 'Research', label: 'All Items', Icon: BarChart3, time: '4 days ago' },
  { cat: 'Assets', label: 'Equities', Icon: LineChart, time: '4 days ago' },
];

// Page

export default function DashboardPage() {
  const { data: econData } = useEconCalendar();
  const econ = econData ?? ECON_FALLBACK;

  return (
    <div className="flex min-h-[calc(100dvh-48px)] flex-col">
      <div className="flex-1 px-5 pt-4">
      <div className="grid grid-cols-[1fr_300px] grid-rows-[auto_auto] gap-x-4 gap-y-4">
        <div className="grid grid-cols-5 gap-3">
          {IDX_SYMBOLS.map((s) => <IdxCard key={s} symbol={s} />)}
        </div>

        <div className={`${card} px-4 py-3`}>
          <div className="flex gap-4">
            <div className="flex-1">
              <h3 className="mb-1.5 text-[13px] font-bold text-[#1e293b]">Support</h3>
              {['Release Notes', 'Submit a Ticket', 'View Tickets', 'Contact Us', 'Support Site', 'Status'].map((l) => (
                <div key={l} className="cursor-pointer py-[2px] text-[12px] text-[#2563eb] hover:underline">{l}</div>
              ))}
            </div>
            <div className="flex-1">
              <h3 className="mb-1.5 text-[13px] font-bold text-[#1e293b]">Discover</h3>
              {['Datasets', 'APIs', 'Models', 'Private i', 'Total Plan', 'Analytics'].map((l) => (
                <div key={l} className="cursor-pointer py-[2px] text-[12px] text-[#2563eb] hover:underline">{l}</div>
              ))}
            </div>
          </div>
        </div>

        <section>
          <div className="section-header">
            <span>Market Research and Insights</span>
            <Link href="/research" className="link-blue">View All</Link>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {ARTICLES.map((a) => (
              <Link key={a.id} href="/research" className="article-card">
                <div className="article-thumb shrink-0" style={{ background: a.gradient }} />
                <div className="article-text">
                  <h3 className="article-title">{a.title}</h3>
                  <p className="article-body">{a.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <div className={`${card} px-4 py-3`}>
          <h3 className="mb-2.5 text-[14px] font-bold text-[#1e293b]">Recently Visited</h3>
          <div className="space-y-2.5">
            {VISITED.map((v, i) => (
              <div key={i} className="flex items-center gap-2.5">
                <v.Icon className="h-4 w-4 shrink-0 text-[#2563eb]" />
                <div className="min-w-0 flex-1">
                  <span className="text-[12px] font-bold text-[#1e293b]">{v.cat}</span>
                  <span className="text-[12px] text-[#64748b]"> {'\u2013'} </span>
                  <span className="cursor-pointer text-[12px] text-[#2563eb] hover:underline">{v.label}</span>
                </div>
                <span className="shrink-0 text-[11px] text-[#94a3b8]">{v.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 items-start gap-4 pb-4">
        <div className="card-base flex flex-col" style={{ padding: 20 }}>
          <h2 className="mb-3 text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>Market Summary</h2>
          <div className="kpi-row">
            <div className="kpi-metric">
              <span className="label-caps" style={{ display: 'block', marginBottom: 4 }}>P/E</span>
              <div className="kpi-value">15.76</div>
            </div>
            <div className="kpi-divider" />
            <div className="kpi-metric">
              <span className="label-caps" style={{ display: 'block', marginBottom: 4 }}>P/BV</span>
              <div className="kpi-value">2.49</div>
            </div>
            <div className="kpi-divider" />
            <div className="kpi-metric">
              <span className="label-caps" style={{ display: 'block', marginBottom: 4 }}>Div Yield</span>
              <div className="kpi-value">3.2%</div>
            </div>
          </div>
          <div className="mt-3">
            <div className="summary-row">
              <span className="summary-row-label">Net Foreign (Week)</span>
              <span className="summary-row-value-positive">+IDR 2,487B</span>
            </div>
            <div className="summary-row">
              <span className="summary-row-label">Trading Value</span>
              <span className="summary-row-value">IDR 11.9T</span>
            </div>
          </div>
          <div className="flow-bar">
            <div style={{ width: '72%', background: 'var(--color-blue-primary)', borderRadius: '3px 0 0 3px', height: '100%' }} />
            <div style={{ width: '28%', background: '#7AB3E0', borderRadius: '0 3px 3px 0', height: '100%' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--color-text-muted)' }}>
            <span>Domestic <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>72%</span></span>
            <span>Foreign <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>28%</span></span>
          </div>
          <div className="mt-3">
            <div className="mb-2 text-[12px] font-semibold" style={{ color: 'var(--color-text-primary)' }}>Top Sectors (Today)</div>
            {[
              { name: 'Banks', pct: 1.24, up: true },
              { name: 'Energy', pct: 0.87, up: true },
              { name: 'Consumer', pct: -0.45, up: false },
              { name: 'Telco', pct: -0.62, up: false },
            ].map((s) => (
              <div key={s.name} className="sector-row">
                <span style={{ fontSize: 12, color: 'var(--color-text-primary)' }}>{s.name}</span>
                <span
                  className="tabular-nums"
                  style={{ fontSize: 12, fontWeight: 600, color: s.up ? 'var(--color-positive)' : 'var(--color-negative)' }}
                >
                  {s.up ? '+' : ''}{s.pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="card-base flex flex-col overflow-hidden" style={{ padding: 0 }}>
          <div
            className="flex items-center justify-between"
            style={{ padding: '12px 14px', borderBottom: '1px solid var(--color-border)' }}
          >
            <h2 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)' }}>Economic Calendar</h2>
            <Link href="#" className="link-blue">View All</Link>
          </div>
          <table className="calendar-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Event</th>
                <th style={{ textAlign: 'right' }}>Prev</th>
                <th style={{ textAlign: 'right' }}>Fcst</th>
                <th style={{ textAlign: 'right' }}>Act</th>
              </tr>
            </thead>
            <tbody>
              {econ.map((row, i) => {
                const lowerBetter = /Rate|LPR|CPI|USD\/IDR/i.test(row.indicator);
                const fc = parseFloat(row.forecast.replace(/,/g, ''));
                const cur = parseFloat(row.current.replace(/,/g, ''));
                const hasBoth = !isNaN(fc) && !isNaN(cur) && cur !== fc;
                const beat = hasBoth && (lowerBetter ? cur < fc : cur > fc);
                const miss = hasBoth && (lowerBetter ? cur > fc : cur < fc);
                const actualColor = beat
                  ? 'var(--color-positive)'
                  : miss
                  ? 'var(--color-negative)'
                  : 'var(--color-text-primary)';
                return (
                  <tr key={i}>
                    <td className="data-mono" style={{ whiteSpace: 'nowrap' }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          color: row.released ? 'var(--color-text-muted)' : 'var(--color-blue-primary)',
                        }}
                      >
                        {row.date}
                      </span>
                    </td>
                    <td>
                      <div className="truncate" style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>
                        {row.indicator}
                      </div>
                    </td>
                    <td className="data-mono calendar-previous" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
                      {fmtNum(row.previous)}{row.unit}
                    </td>
                    <td className="data-mono calendar-forecast" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
                      {fmtNum(row.forecast)}{row.unit}
                    </td>
                    {row.released ? (
                      <td
                        className="data-mono calendar-actual"
                        style={{ whiteSpace: 'nowrap', textAlign: 'right', color: actualColor }}
                      >
                        {fmtNum(row.current)}{row.unit}
                      </td>
                    ) : (
                      <td className="data-mono calendar-empty">{'\u2014'}</td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="card-base flex flex-col" style={{ padding: 16 }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
            <h2 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)' }}>IPO & Corporate Actions</h2>
            <Link href="#" className="link-blue">View All</Link>
          </div>
          <div className="flex-1">
            {ACTIONS.map((a, i) => {
              const [desc, ex] = a.detail.split(' \u00b7 ');
              const hasTicker = a.sym !== '\u2014';
              return (
                <div key={i} className="action-row">
                  <span className="action-date">{a.date}</span>
                  {hasTicker ? (
                    <span className="ticker-badge">{a.sym}</span>
                  ) : (
                    <span style={{ display: 'inline-block', minWidth: 44 }} />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="action-title">{a.act}</div>
                    <div className="action-desc">
                      {desc}
                      {ex ? <span className="action-ex">{ex}</span> : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      </div>

      <footer className="shrink-0 border-t border-[#e2e8f0] bg-[#f8fafc] px-5 py-3">
        <p className="text-center text-[12px] text-[#64748b]">
          &copy; 2026 Pyhron Inc. All Rights Reserved. Subject to{' '}
          <a href="/terms" className="text-[#2563eb] underline hover:text-[#1d4ed8]">Terms of Use</a> &amp;{' '}
          <a href="/disclaimer" className="text-[#2563eb] underline hover:text-[#1d4ed8]">Disclaimer</a>.{' '}
          <a href="#" className="text-[#2563eb] underline hover:text-[#1d4ed8]">Manage Cookies</a>.
        </p>
      </footer>
    </div>
  );
}
