'use client';

import Link from 'next/link';
import { Building2, LineChart, BarChart3 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

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

function useEconCalendar() {
  return useQuery<{ indicator: string; unit: string; current: string; previous: string; forecast: string; date: string }[]>({
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
  const n = parseFloat(v.replace(/,/g, ''));
  if (isNaN(n)) return v;
  if (Math.abs(n) >= 10000) return n.toLocaleString('en-US', { maximumFractionDigits: 0 });
  if (Math.abs(n) >= 100) return n.toFixed(1);
  return n.toFixed(2);
}

function smoothPath(coords: { x: number; y: number }[]): string {
  if (coords.length === 0) return '';
  if (coords.length === 1) return `M${coords[0].x},${coords[0].y}`;
  let d = `M${coords[0].x.toFixed(2)},${coords[0].y.toFixed(2)}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i - 1] ?? coords[i];
    const p1 = coords[i];
    const p2 = coords[i + 1];
    const p3 = coords[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }
  return d;
}

function SvgSpark({ pts, up, w = 300, h = 55 }: { pts: number[]; up: boolean; w?: number; h?: number }) {
  if (pts.length < 2) return <div style={{ height: h }} className="w-full" />;
  const mn = Math.min(...pts);
  const mx = Math.max(...pts);
  const rng = mx - mn || 1;
  const padY = h * 0.12;
  const coords = pts.map((p, i) => ({
    x: (i / (pts.length - 1)) * w,
    y: padY + (h - padY * 2) - ((p - mn) / rng) * (h - padY * 2),
  }));
  const line = smoothPath(coords);
  const fill = `${line} L${w.toFixed(2)},${h} L0,${h} Z`;
  const clr = up ? '#16a34a' : '#dc2626';
  const gid = `g-${up ? 'u' : 'd'}-${Math.round(mn * 100)}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="block w-full" style={{ height: h }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={clr} stopOpacity="0.22" />
          <stop offset="100%" stopColor={clr} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fill} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={clr} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
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
  const n = 78;
  const open = fb.base / (1 + fb.change / 100);
  const target = fb.base;
  const rand = seeded(symbol.charCodeAt(0) * 31 + symbol.charCodeAt(1));
  const vol = fb.base * 0.0015;
  const out: number[] = [open];
  for (let i = 1; i < n; i++) {
    const t = i / (n - 1);
    const drift = (target - open) * t;
    const noise = (rand() - 0.5) * vol * 2;
    const wave = Math.sin(i * 0.35) * fb.base * 0.0012 + Math.sin(i * 0.11) * fb.base * 0.0018;
    out.push(Math.round((open + drift + noise + wave) * 100) / 100);
  }
  out[n - 1] = target;
  return out;
}

function IdxCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useIdx(symbol);
  const fb = IDX_FALLBACK[symbol] ?? { base: 0, change: 0 };
  const cur = data?.current && data.current > 0 ? data.current : fb.base;
  const chg = data?.change ?? fb.change;
  const apiPts = data?.points ?? [];
  const pts = apiPts.length >= 2 ? apiPts : fallbackPts(symbol);
  const ts = data?.lastUpdate ?? '--:--';
  const up = chg >= 0;

  return (
    <div className={`${card} overflow-hidden`}>
      <div className="px-4 pt-3 pb-1">
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-[13px] font-bold uppercase text-[#1e293b]">{symbol}</span>
          <span className="text-[12px] tabular-nums text-[#94a3b8]">{ts}</span>
        </div>
        {isLoading && !data ? (
          <div className="space-y-1.5">
            <div className="h-5 w-24 animate-pulse rounded bg-[#e2e8f0]" />
            <div className="h-4 w-16 animate-pulse rounded bg-[#e2e8f0]" />
          </div>
        ) : (
          <div className="flex items-baseline gap-3">
            <span className="text-[18px] font-semibold tabular-nums text-[#0f172a]">
              {cur.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`text-[13px] font-medium tabular-nums ${up ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
              {up ? '▲' : '▼'} {up ? '+' : ''}{chg.toFixed(2)}%
            </span>
          </div>
        )}
      </div>
      <div className="mt-2">
        <SvgSpark pts={pts} up={up} h={50} />
      </div>
    </div>
  );
}

// Data

const IDX_SYMBOLS = ['IHSG', 'LQ45', 'IDX30', 'IDX80', 'JII'];

const ARTICLES = [
  { id: 'prop', title: 'Latest on Indonesian Commercial-Property Pricing', desc: 'We report the latest trends in the RCA CPPI for Indonesia. We cover the all-property index and indexes for the major property types including industrial, retail, apartment and office.', bg: '#1e3a5f' },
  { id: 'carbon', title: 'Carbon-Credit Integrity in the ACCU Market', desc: 'Integrity matters in compliance markets. MSCI Carbon Markets\u2019 analysis of ACCU ARR projects reveals pricing premiums, project-level risk variation and how methodology design shapes outcomes.', bg: '#2d4a3e' },
  { id: 'gap', title: 'The Transparency Gap: GP Data Rooms', desc: 'Transparency has become one of the defining challenges in the relationship between GPs and LPs in private markets. This analysis identifies where the data falls short during due diligence.', bg: '#3d2e5c' },
  { id: 'energy', title: 'Positioning Portfolios for the Energy Transition', desc: 'Do funds better positioned for the energy transition outperform? We introduce a forward-looking quadrant framework to assess transition risk and readiness \u2014 and their portfolio implications.', bg: '#4a3328' },
];

const ECON_FALLBACK = [
  { indicator: 'BI Rate', unit: '%', current: '5.75', previous: '5.75', forecast: '5.75', date: 'Mar 2026' },
  { indicator: 'Indonesia CPI', unit: '', current: '133.5', previous: '131.9', forecast: '132.8', date: 'Mar 2026' },
  { indicator: 'Fed Funds Rate', unit: '%', current: '4.50', previous: '4.50', forecast: '4.50', date: 'Mar 2026' },
  { indicator: 'China LPR', unit: '%', current: '3.10', previous: '3.10', forecast: '3.10', date: 'Apr 2026' },
  { indicator: 'Indonesia GDP', unit: '%', current: '5.11', previous: '5.05', forecast: '5.08', date: 'Q4 2025' },
  { indicator: 'USD/IDR', unit: '', current: '15,380', previous: '15,420', forecast: '15,450', date: 'Apr 2026' },
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
    <div className="flex h-[calc(100dvh-48px)] flex-col">
      <div className="flex flex-1 min-h-0 flex-col px-5 pt-5">
      <div className="grid grid-cols-[1fr_300px] gap-4">
        <div className="space-y-4">

          <div className="grid grid-cols-5 gap-3">
            {IDX_SYMBOLS.map((s) => <IdxCard key={s} symbol={s} />)}
          </div>

          <div className={card}>
            <div className="flex items-center justify-between border-b border-[#e2e8f0] px-5 py-3">
              <h2 className="text-[15px] font-semibold text-[#1e293b]">Market Research and Insights</h2>
              <Link href="/research" className="text-[13px] font-medium text-[#2563eb] hover:underline">View All</Link>
            </div>
            <div className="grid grid-cols-2">
              {ARTICLES.map((a, i) => (
                <Link key={a.id} href="/research"
                  className={`group flex gap-4 p-5 transition-colors hover:bg-[#f8fafc] ${i % 2 === 0 ? 'border-r border-[#e2e8f0]' : ''} ${i < 2 ? 'border-b border-[#e2e8f0]' : ''}`}>
                  <div className="h-[90px] w-[120px] shrink-0 rounded-lg" style={{ backgroundColor: a.bg }} />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[15px] font-bold leading-snug text-[#1e3a8a] group-hover:underline">{a.title}</h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-[#64748b] line-clamp-3">{a.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className={`${card} p-4`}>
            <div className="flex gap-6">
              <div className="flex-1">
                <h3 className="mb-2 text-[14px] font-bold text-[#1e293b]">Support</h3>
                {['Release Notes', 'Submit a Support Ticket', 'View Support Tickets', 'Contact Us', 'Support Site', 'Platform Status'].map((l) => (
                  <div key={l} className="cursor-pointer py-[3px] text-[13px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
              <div className="flex-1">
                <h3 className="mb-2 text-[14px] font-bold text-[#1e293b]">Discover</h3>
                {['Datasets', 'APIs', 'Models', 'Private i', 'Total Plan', 'Capital Analytics'].map((l) => (
                  <div key={l} className="cursor-pointer py-[3px] text-[13px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
            </div>
          </div>

          <div className={`${card} p-4`}>
            <h3 className="mb-3 text-[15px] font-bold text-[#1e293b]">Recently Visited</h3>
            <div className="space-y-3">
              {VISITED.map((v, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <v.Icon className="h-4 w-4 shrink-0 text-[#2563eb]" />
                  <div className="min-w-0 flex-1">
                    <span className="text-[13px] font-bold text-[#1e293b]">{v.cat}</span>
                    <span className="text-[13px] text-[#64748b]"> - </span>
                    <span className="cursor-pointer text-[13px] text-[#2563eb] hover:underline">{v.label}</span>
                  </div>
                  <span className="shrink-0 text-[12px] text-[#94a3b8]">{v.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid flex-1 grid-cols-3 gap-4 min-h-0">
        <div className={`${card} flex flex-col p-4`}>
          <h2 className="mb-2.5 text-[15px] font-bold text-[#1e293b]">Market Summary</h2>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-md bg-[#f8fafc] px-2 py-1.5">
              <div className="text-[10px] uppercase tracking-wide text-[#94a3b8]">P/E</div>
              <div className="text-[15px] font-semibold tabular-nums text-[#0f172a]">15.76</div>
            </div>
            <div className="rounded-md bg-[#f8fafc] px-2 py-1.5">
              <div className="text-[10px] uppercase tracking-wide text-[#94a3b8]">P/BV</div>
              <div className="text-[15px] font-semibold tabular-nums text-[#0f172a]">2.49</div>
            </div>
            <div className="rounded-md bg-[#f8fafc] px-2 py-1.5">
              <div className="text-[10px] uppercase tracking-wide text-[#94a3b8]">Div Yield</div>
              <div className="text-[15px] font-semibold tabular-nums text-[#0f172a]">3.2%</div>
            </div>
          </div>
          <div className="mt-2.5 border-t border-[#f1f5f9] pt-2">
            <div className="flex items-baseline justify-between">
              <span className="text-[12px] font-semibold text-[#1e293b]">Net Foreign This Week</span>
              <span className="text-[14px] font-bold tabular-nums text-[#16a34a]">+IDR 2,487B</span>
            </div>
          </div>
          <div className="mt-2 border-t border-[#f1f5f9] pt-2">
            <div className="flex items-baseline justify-between">
              <span className="text-[12px] font-semibold text-[#1e293b]">Trading Value</span>
              <span className="text-[14px] font-semibold tabular-nums text-[#0f172a]">IDR 11.9T</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-[#f1f5f9]">
              <div className="h-full bg-[#2563eb]" style={{ width: '72%' }} />
            </div>
            <div className="mt-1 flex justify-between text-[11px] text-[#64748b]">
              <span>Domestic <span className="font-semibold text-[#1e293b]">72%</span></span>
              <span>Foreign <span className="font-semibold text-[#1e293b]">28%</span></span>
            </div>
          </div>
          <div className="mt-2.5 flex-1 border-t border-[#f1f5f9] pt-2">
            <div className="mb-1.5 text-[12px] font-semibold text-[#1e293b]">Top Sectors (Today)</div>
            <div className="space-y-1">
              {[
                { name: 'Banks', pct: 1.24, up: true },
                { name: 'Energy', pct: 0.87, up: true },
                { name: 'Consumer', pct: -0.45, up: false },
                { name: 'Telco', pct: -0.62, up: false },
              ].map((s) => (
                <div key={s.name} className="flex items-center justify-between text-[12px]">
                  <span className="text-[#475569]">{s.name}</span>
                  <span className={`font-semibold tabular-nums ${s.up ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
                    {s.up ? '+' : ''}{s.pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className={`${card} flex flex-col p-4`}>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#1e293b]">Economic Calendar</h2>
            <span className="cursor-pointer text-[12px] text-[#2563eb] hover:underline">View All</span>
          </div>
          <table className="w-full table-fixed">
            <thead>
              <tr className="border-b border-[#e2e8f0]">
                <th className="w-[40%] pb-1.5 text-left text-[10px] font-semibold uppercase text-[#94a3b8]">Indicator</th>
                <th className="pb-1.5 text-right text-[10px] font-semibold uppercase text-[#94a3b8]">Prev</th>
                <th className="pb-1.5 text-right text-[10px] font-semibold uppercase text-[#94a3b8]">Fcst</th>
                <th className="pb-1.5 text-right text-[10px] font-semibold uppercase text-[#94a3b8]">Actual</th>
              </tr>
            </thead>
            <tbody>
              {econ.map((row, i) => {
                const lowerBetter = /CPI|Rate|USD\/IDR|LPR/i.test(row.indicator);
                const fc = parseFloat(row.forecast.replace(/,/g, ''));
                const cur = parseFloat(row.current.replace(/,/g, ''));
                const hasBoth = !isNaN(fc) && !isNaN(cur) && cur !== fc;
                const beat = hasBoth && (lowerBetter ? cur < fc : cur > fc);
                const miss = hasBoth && (lowerBetter ? cur > fc : cur < fc);
                const color = beat ? 'text-[#16a34a]' : miss ? 'text-[#dc2626]' : 'text-[#0f172a]';
                return (
                  <tr key={i} className="border-b border-[#f1f5f9] last:border-0">
                    <td className="py-1.5 pr-1">
                      <div className="truncate text-[12px] font-medium text-[#1e293b]">{row.indicator}</div>
                      <div className="text-[10px] text-[#94a3b8]">{row.date}</div>
                    </td>
                    <td className="py-1.5 text-right text-[12px] tabular-nums text-[#475569]">{fmtNum(row.previous)}{row.unit}</td>
                    <td className="py-1.5 text-right text-[12px] tabular-nums text-[#94a3b8]">{fmtNum(row.forecast)}{row.unit}</td>
                    <td className={`py-1.5 text-right text-[12px] font-semibold tabular-nums ${color}`}>{fmtNum(row.current)}{row.unit}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className={`${card} flex flex-col p-4`}>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#1e293b]">IPO & Corporate Actions</h2>
            <span className="cursor-pointer text-[12px] text-[#2563eb] hover:underline">View All</span>
          </div>
          <div className="flex-1">
            {ACTIONS.map((a, i) => (
              <div key={i} className="flex items-start gap-3 border-b border-[#f1f5f9] py-1.5 last:border-0">
                <span className="w-[46px] shrink-0 text-[12px] tabular-nums text-[#94a3b8]">{a.date}</span>
                <span className="w-[42px] shrink-0 text-[12px] font-bold text-[#2563eb]">{a.sym}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-medium text-[#1e293b]">{a.act}</div>
                  <div className="text-[11px] text-[#94a3b8]">{a.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      </div>

      <footer className="mt-4 shrink-0 border-t border-[#e2e8f0] bg-[#f8fafc] px-5 py-3">
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
