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
  return useQuery<{ indicator: string; unit: string; current: string; previous: string; date: string }[]>({
    queryKey: ['econ-calendar'],
    queryFn: async () => {
      const r = await fetch('/api/v1/markets/economic-calendar');
      if (!r.ok) throw new Error('fetch failed');
      return r.json();
    },
    staleTime: 3600_000,
  });
}

function SvgSpark({ pts, up, w = 200, h = 55 }: { pts: number[]; up: boolean; w?: number; h?: number }) {
  if (pts.length < 2) return null;
  const mn = Math.min(...pts);
  const mx = Math.max(...pts);
  const rng = mx - mn || 1;
  const coords = pts.map((p, i) => ({
    x: (i / (pts.length - 1)) * w,
    y: 2 + (h - 4) - ((p - mn) / rng) * (h - 4),
  }));
  const line = coords.map((v, i) => `${i === 0 ? 'M' : 'L'}${v.x.toFixed(1)},${v.y.toFixed(1)}`).join(' ');
  const fill = `${line} L${w},${h} L0,${h} Z`;
  const clr = up ? '#16a34a' : '#dc2626';
  const gid = `g-${up ? 'u' : 'd'}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: h }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={clr} stopOpacity="0.18" />
          <stop offset="100%" stopColor={clr} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fill} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={clr} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IdxCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useIdx(symbol);
  const cur = data?.current ?? 0;
  const chg = data?.change ?? 0;
  const pts = data?.points ?? [];
  const ts = data?.lastUpdate ?? '--:--';
  const up = chg >= 0;

  return (
    <div className={`${card} overflow-hidden`}>
      <div className="px-4 pt-3 pb-1">
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-[13px] font-bold uppercase text-[#1e293b]">{symbol}</span>
          <span className="text-[12px] tabular-nums text-[#94a3b8]">{ts}</span>
        </div>
        {isLoading ? (
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
      <div className="mt-1">
        {pts.length >= 2 ? <SvgSpark pts={pts} up={up} h={55} /> : <div className="h-[55px] w-full animate-pulse bg-[#f8fafc]" />}
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
  { indicator: 'BI 7-Day Repo Rate', unit: '%', current: '5.75', previous: '5.75', date: '2026-03' },
  { indicator: 'Indonesia CPI', unit: '%', current: '2.47', previous: '2.68', date: '2026-03' },
  { indicator: 'Indonesia GDP', unit: 'B IDR', current: '5.02', previous: '4.94', date: '2025-Q4' },
  { indicator: 'USD/IDR Exchange Rate', unit: '', current: '15420', previous: '15480', date: '2026-04' },
  { indicator: 'China Loan Prime Rate', unit: '%', current: '3.10', previous: '3.10', date: '2026-04' },
  { indicator: 'Fed Funds Rate', unit: '%', current: '4.50', previous: '4.50', date: '2026-03' },
];

const ACTIONS = [
  { date: 'Apr 18', sym: 'BBCA', act: 'Cash Dividend', detail: 'IDR 180/share' },
  { date: 'Apr 22', sym: 'BMRI', act: 'Rights Issue', detail: '1:4 ratio' },
  { date: 'Apr 25', sym: '\u2014', act: 'LQ45 Rebalancing', detail: 'Effective date' },
  { date: 'May 2', sym: 'TLKM', act: 'Cash Dividend', detail: 'IDR 95/share' },
  { date: 'May 15', sym: '\u2014', act: 'IDX80 Review', detail: 'Semi-annual' },
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
    <div className="flex h-[calc(100dvh-48px)] flex-col p-5 pb-0">
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
        <div className={`${card} flex flex-col p-5`}>
          <h2 className="mb-3 text-[15px] font-bold text-[#1e293b]">Market Summary</h2>
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <div className="text-[11px] text-[#94a3b8]">Market P/E</div>
                <div className="text-[16px] font-semibold tabular-nums text-[#0f172a]">15.76</div>
              </div>
              <div>
                <div className="text-[11px] text-[#94a3b8]">Market P/BV</div>
                <div className="text-[16px] font-semibold tabular-nums text-[#0f172a]">2.49</div>
              </div>
              <div>
                <div className="text-[11px] text-[#94a3b8]">Dividend Yield</div>
                <div className="text-[16px] font-semibold tabular-nums text-[#0f172a]">3.2%</div>
              </div>
            </div>
            <div className="border-t border-[#f1f5f9] pt-3">
              <div className="text-[12px] font-semibold text-[#1e293b]">Net Foreign This Week</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-[18px] font-bold tabular-nums text-[#16a34a]">+IDR 2,487B</span>
                <span className="text-[12px] text-[#94a3b8]">Net Buy</span>
              </div>
            </div>
            <div className="border-t border-[#f1f5f9] pt-3">
              <div className="text-[12px] font-semibold text-[#1e293b]">Trading Value (Daily Avg)</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-[16px] font-semibold tabular-nums text-[#0f172a]">IDR 11.9T</span>
              </div>
              <div className="mt-1.5 flex gap-4 text-[12px]">
                <span className="text-[#475569]">Domestic: <span className="font-semibold">72%</span></span>
                <span className="text-[#475569]">Foreign: <span className="font-semibold">28%</span></span>
              </div>
            </div>
          </div>
        </div>

        <div className={`${card} flex flex-col overflow-hidden p-5`}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#1e293b]">Economic Calendar</h2>
            <span className="cursor-pointer text-[12px] text-[#2563eb] hover:underline">View All</span>
          </div>
          <div className="flex-1 overflow-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#e2e8f0]">
                  <th className="pb-2 text-left text-[11px] font-semibold uppercase text-[#94a3b8]">Indicator</th>
                  <th className="pb-2 text-right text-[11px] font-semibold uppercase text-[#94a3b8]">Previous</th>
                  <th className="pb-2 text-right text-[11px] font-semibold uppercase text-[#94a3b8]">Actual</th>
                </tr>
              </thead>
              <tbody>
                {econ.map((row, i) => {
                  const prev = parseFloat(row.previous);
                  const cur = parseFloat(row.current);
                  const better = !isNaN(prev) && !isNaN(cur) && cur !== prev;
                  const color = better ? (cur > prev ? 'text-[#16a34a]' : 'text-[#dc2626]') : 'text-[#0f172a]';
                  return (
                    <tr key={i} className="border-b border-[#f1f5f9] last:border-0">
                      <td className="py-2 pr-2">
                        <div className="text-[13px] text-[#1e293b]">{row.indicator}</div>
                        <div className="text-[11px] text-[#94a3b8]">{row.date}</div>
                      </td>
                      <td className="py-2 text-right text-[13px] tabular-nums text-[#475569]">{row.previous}{row.unit ? row.unit : ''}</td>
                      <td className={`py-2 text-right text-[13px] font-semibold tabular-nums ${color}`}>{row.current}{row.unit ? row.unit : ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className={`${card} flex flex-col overflow-hidden p-5`}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#1e293b]">IPO & Corporate Actions</h2>
            <span className="cursor-pointer text-[12px] text-[#2563eb] hover:underline">View All</span>
          </div>
          <div className="flex-1 overflow-auto">
            {ACTIONS.map((a, i) => (
              <div key={i} className="flex items-start gap-3 border-b border-[#f1f5f9] py-2.5 last:border-0">
                <span className="w-[46px] shrink-0 text-[12px] tabular-nums text-[#94a3b8]">{a.date}</span>
                <span className="w-[42px] shrink-0 text-[12px] font-bold text-[#2563eb]">{a.sym}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium text-[#1e293b]">{a.act}</div>
                  <div className="text-[12px] text-[#94a3b8]">{a.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="shrink-0 py-3">
        <p className="text-center text-[12px] text-[#94a3b8]">
          &copy; 2026 Pyhron Inc. All Rights Reserved. Subject to{' '}
          <span className="cursor-pointer underline">Terms of Use</span> &amp;{' '}
          <span className="cursor-pointer underline">Disclaimer</span>.{' '}
          <span className="cursor-pointer underline">Manage Cookies</span>.
        </p>
      </div>
    </div>
  );
}
