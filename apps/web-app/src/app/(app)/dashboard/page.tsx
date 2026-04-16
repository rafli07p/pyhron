'use client';

import Link from 'next/link';
import { Building2, LineChart, BarChart3 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

/* ═══ STYLE ═══ */
const card = 'rounded-[15px] border border-[#e2e8f0] bg-white';

/* ═══ MARKET HOURS ═══ */
function isIDXOpen(): boolean {
  const now = new Date();
  const h = (now.getUTCHours() + 7) % 24;
  const m = now.getUTCMinutes();
  const d = now.getDay();
  if (d === 0 || d === 6) return false;
  const t = h * 60 + m;
  return (t >= 540 && t <= 690) || (t >= 810 && t <= 910);
}

/* ═══ INTRADAY HOOK ═══ */
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

/* ═══ SPARKLINE ═══ */
function SvgSpark({ pts, up, w = 200, h = 48 }: { pts: number[]; up: boolean; w?: number; h?: number }) {
  if (pts.length < 2) return null;
  const mn = Math.min(...pts);
  const mx = Math.max(...pts);
  const rng = mx - mn || 1;
  const pad = 2;
  const cH = h - pad * 2;
  const coords = pts.map((p, i) => ({
    x: (i / (pts.length - 1)) * w,
    y: pad + cH - ((p - mn) / rng) * cH,
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

/* ═══ INDEX CARD ═══ */
function IdxCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useIdx(symbol);
  const cur = data?.current ?? 0;
  const chg = data?.change ?? 0;
  const pts = data?.points ?? [];
  const ts = data?.lastUpdate ?? '--:--';
  const up = chg >= 0;

  return (
    <div className={`${card} overflow-hidden`}>
      <div className="px-3.5 pt-3 pb-0.5">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[13px] font-bold uppercase tracking-wide text-[#1e293b]">{symbol}</span>
          <span className="text-[11px] tabular-nums text-[#94a3b8]">{ts}</span>
        </div>
        {isLoading ? (
          <div className="space-y-1.5">
            <div className="h-5 w-24 animate-pulse rounded bg-[#e2e8f0]" />
            <div className="h-3.5 w-16 animate-pulse rounded bg-[#e2e8f0]" />
          </div>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className="text-[17px] font-semibold tabular-nums text-[#0f172a]">
              {cur.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`text-[12px] font-medium tabular-nums ${up ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
              {up ? '▲' : '▼'} {up ? '+' : ''}{chg.toFixed(2)}%
            </span>
          </div>
        )}
      </div>
      <div className="mt-0.5">
        {pts.length >= 2 ? (
          <SvgSpark pts={pts} up={up} h={48} />
        ) : (
          <div className="h-[48px] w-full animate-pulse bg-[#f1f5f9]" />
        )}
      </div>
    </div>
  );
}

/* ═══ DATA ═══ */
const IDX_SYMBOLS = ['IHSG', 'LQ45', 'IDX30', 'IDX80', 'JII'];

const ARTICLES = [
  { id: 'prop', title: 'Latest on Indonesian Commercial-Property Pricing', desc: 'We report the latest trends in the RCA CPPI for Indonesia. We cover the all-property index and indexes for the major property types including industrial, retail, apartment and office.', bg: '#1e3a5f' },
  { id: 'carbon', title: 'Carbon-Credit Integrity in the ACCU Market', desc: 'Integrity matters in compliance markets. Analysis of ACCU ARR projects reveals pricing premiums, project-level risk variation and how methodology design shapes outcomes.', bg: '#2d4a3e' },
  { id: 'gap', title: 'The Transparency Gap: GP Data Rooms', desc: 'Transparency has become one of the defining challenges in the relationship between GPs and LPs in private markets. This analysis identifies where the data falls short.', bg: '#3d2e5c' },
  { id: 'energy', title: 'Positioning Portfolios for the Energy Transition', desc: 'Do funds better positioned for the energy transition outperform? We introduce a forward-looking quadrant framework to assess transition risk and readiness.', bg: '#4a3328' },
];

const ECON_DATA: { indicator: string; period: string; previous: string; actual: string; forecast: string; actualColor: 'green' | 'red' | 'neutral' }[] = [
  { indicator: 'BI 7-Day Reverse Repo Rate', period: 'APR', previous: '5.75%', actual: '5.75%', forecast: '5.75%', actualColor: 'neutral' },
  { indicator: 'Indonesia CPI YoY', period: 'MAR', previous: '2.68%', actual: '2.47%', forecast: '2.50%', actualColor: 'green' },
  { indicator: 'Indonesia GDP Growth YoY', period: 'Q4', previous: '4.94%', actual: '5.02%', forecast: '4.98%', actualColor: 'green' },
  { indicator: 'Foreign Bond Investment', period: 'MAR', previous: 'IDR 2.1T', actual: 'IDR 3.8T', forecast: '', actualColor: 'green' },
  { indicator: 'Stock Investment by Foreigners', period: 'MAR', previous: 'IDR -1.2T', actual: 'IDR -2.4T', forecast: '', actualColor: 'red' },
  { indicator: 'Trade Balance', period: 'MAR', previous: '$3.56B', actual: '$3.21B', forecast: '$3.40B', actualColor: 'red' },
  { indicator: 'Indonesia Manufacturing PMI', period: 'APR', previous: '52.4', actual: '51.9', forecast: '52.2', actualColor: 'red' },
  { indicator: 'Rupiah Exchange Rate (USD)', period: 'APR', previous: '15,480', actual: '15,420', forecast: '15,450', actualColor: 'green' },
  { indicator: 'China Loan Prime Rate 1Y', period: 'APR', previous: '3.10%', actual: '3.10%', forecast: '3.10%', actualColor: 'neutral' },
  { indicator: 'Fed Funds Rate', period: 'MAR', previous: '4.50%', actual: '4.50%', forecast: '4.50%', actualColor: 'neutral' },
];

const VISITED = [
  { cat: 'Companies', label: 'Index Composition Viewer', Icon: Building2, time: '1 day ago' },
  { cat: 'Research', label: 'All Items', Icon: BarChart3, time: '2 days ago' },
  { cat: 'Assets', label: 'Equities', Icon: LineChart, time: '3 days ago' },
];

/* ═══ PAGE ═══ */
export default function DashboardPage() {
  return (
    <div className="flex h-[calc(100dvh-48px)] flex-col p-4 pb-0">
      {/* TOP: Index cards + Sidebar */}
      <div className="grid grid-cols-[1fr_280px] gap-3">
        {/* LEFT */}
        <div className="space-y-3">
          {/* Index Cards */}
          <div className="grid grid-cols-5 gap-3">
            {IDX_SYMBOLS.map((s) => <IdxCard key={s} symbol={s} />)}
          </div>

          {/* Market Research */}
          <div className={card}>
            <div className="flex items-center justify-between border-b border-[#e2e8f0] px-4 py-2.5">
              <h2 className="text-[15px] font-semibold text-[#1e293b]">Market Research and Insights</h2>
              <Link href="/research" className="text-[13px] font-medium text-[#2563eb] hover:underline">View All</Link>
            </div>
            <div className="grid grid-cols-2">
              {ARTICLES.map((a, i) => (
                <Link key={a.id} href="/research"
                  className={`group flex gap-3 px-4 py-3 transition-colors hover:bg-[#f8fafc] ${i % 2 === 0 ? 'border-r border-[#e2e8f0]' : ''} ${i < 2 ? 'border-b border-[#e2e8f0]' : ''}`}>
                  <div className="h-[65px] w-[90px] shrink-0 rounded-lg" style={{ backgroundColor: a.bg }} />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[13px] font-bold leading-snug text-[#1e3a8a] group-hover:underline line-clamp-2">{a.title}</h3>
                    <p className="mt-1 text-[12px] leading-relaxed text-[#64748b] line-clamp-2">{a.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="space-y-3">
          <div className={`${card} p-3.5`}>
            <div className="flex gap-5">
              <div className="flex-1">
                <h3 className="mb-1.5 text-[13px] font-bold text-[#1e293b]">Support</h3>
                {['Release Notes', 'Submit a Support Ticket', 'View Support Tickets', 'Contact Us', 'Support Site', 'Platform Status'].map((l) => (
                  <div key={l} className="cursor-pointer py-[2px] text-[13px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
              <div className="flex-1">
                <h3 className="mb-1.5 text-[13px] font-bold text-[#1e293b]">Discover</h3>
                {['Datasets', 'APIs', 'Models', 'Screener', 'Total Plan', 'Analytics'].map((l) => (
                  <div key={l} className="cursor-pointer py-[2px] text-[13px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
            </div>
          </div>

          <div className={`${card} p-3.5`}>
            <h3 className="mb-2 text-[14px] font-bold text-[#1e293b]">Recently Visited</h3>
            <div className="space-y-2.5">
              {VISITED.map((v, i) => (
                <div key={i} className="flex items-center gap-2">
                  <v.Icon className="h-4 w-4 shrink-0 text-[#2563eb]" />
                  <div className="min-w-0 flex-1">
                    <span className="text-[13px] font-bold text-[#1e293b]">{v.cat}</span>
                    <span className="text-[13px] text-[#64748b]"> - </span>
                    <span className="cursor-pointer text-[13px] text-[#2563eb] hover:underline">{v.label}</span>
                  </div>
                  <span className="shrink-0 text-[11px] text-[#94a3b8]">{v.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM: Economic Calendar (full width, table format) */}
      <div className={`${card} mt-3 flex-1 overflow-hidden`}>
        <div className="flex items-center justify-between border-b border-[#e2e8f0] px-4 py-2.5">
          <h2 className="text-[15px] font-semibold text-[#1e293b]">Economic Calendar</h2>
          <span className="text-[12px] text-[#64748b]">Indonesia &amp; Global Impact</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#e2e8f0] bg-[#f8fafc]">
                <th className="px-4 py-2 text-left text-[12px] font-semibold text-[#64748b]">Indicator</th>
                <th className="px-4 py-2 text-right text-[12px] font-semibold text-[#64748b]">Previous</th>
                <th className="px-4 py-2 text-right text-[12px] font-semibold text-[#64748b]">Actual</th>
                <th className="px-4 py-2 text-right text-[12px] font-semibold text-[#64748b]">Forecast</th>
              </tr>
            </thead>
            <tbody>
              {ECON_DATA.map((row, i) => (
                <tr key={i} className="border-b border-[#f1f5f9] last:border-0 hover:bg-[#f8fafc] transition-colors">
                  <td className="px-4 py-2">
                    <span className="text-[13px] text-[#1e293b]">{row.indicator}</span>
                    <span className="ml-1.5 text-[10px] font-medium text-[#94a3b8]">{row.period}</span>
                  </td>
                  <td className="px-4 py-2 text-right text-[13px] tabular-nums text-[#475569]">{row.previous}</td>
                  <td className={`px-4 py-2 text-right text-[13px] font-semibold tabular-nums ${
                    row.actualColor === 'green' ? 'text-[#16a34a]' :
                    row.actualColor === 'red' ? 'text-[#dc2626]' :
                    'text-[#1e293b]'
                  }`}>{row.actual}</td>
                  <td className="px-4 py-2 text-right text-[13px] tabular-nums text-[#475569]">{row.forecast || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FOOTER */}
      <div className="shrink-0 py-2.5">
        <p className="text-center text-[11px] text-[#94a3b8]">
          &copy; 2026 Pyhron Inc. All Rights Reserved. Subject to{' '}
          <span className="cursor-pointer underline">Terms of Use</span> &amp;{' '}
          <span className="cursor-pointer underline">Disclaimer</span>.{' '}
          <span className="cursor-pointer underline">Manage Cookies</span>.
        </p>
      </div>
    </div>
  );
}
