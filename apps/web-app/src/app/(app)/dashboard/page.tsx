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
function SvgSpark({ pts, up, w = 200, h = 60 }: { pts: number[]; up: boolean; w?: number; h?: number }) {
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
      <div className="px-4 pt-3.5 pb-1">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-[13px] font-bold uppercase tracking-wide text-[#1e293b]">{symbol}</span>
          <span className="text-[12px] tabular-nums text-[#94a3b8]">{ts}</span>
        </div>
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-6 w-28 animate-pulse rounded bg-[#e2e8f0]" />
            <div className="h-4 w-20 animate-pulse rounded bg-[#e2e8f0]" />
          </div>
        ) : (
          <div className="flex items-baseline gap-2.5">
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
        {pts.length >= 2 ? (
          <SvgSpark pts={pts} up={up} h={60} />
        ) : (
          <div className="h-[60px] w-full animate-pulse bg-[#f1f5f9]" />
        )}
      </div>
    </div>
  );
}

/* ═══ DATA ═══ */
const IDX_SYMBOLS = ['IHSG', 'LQ45', 'IDX30', 'IDX80', 'JII'];

const ARTICLES = [
  { id: 'prop', title: 'Latest on Indonesian Commercial-Property Pricing', desc: 'We report the latest trends in the RCA CPPI for Indonesia. We cover the all-property index and indexes for the major property types including industrial, retail, apartment and office.', bg: '#1e3a5f' },
  { id: 'carbon', title: 'Carbon-Credit Integrity in the ACCU Market', desc: 'Integrity matters in compliance markets. MSCI Carbon Markets\u2019 analysis of ACCU ARR projects reveals pricing premiums, project-level risk variation and how methodology design shapes outcomes.', bg: '#2d4a3e' },
  { id: 'gap', title: 'The Transparency Gap: GP Data Rooms', desc: 'Transparency has become one of the defining challenges in the relationship between GPs and LPs in private markets. This analysis identifies where the data falls short during due diligence.', bg: '#3d2e5c' },
  { id: 'energy', title: 'Positioning Portfolios for the Energy Transition', desc: 'Do funds better positioned for the energy transition outperform? We introduce a forward-looking quadrant framework to assess transition risk and readiness \u2014 and their portfolio implications.', bg: '#4a3328' },
];

const FEATURES = [
  { title: 'Explore Market Insights', desc: 'Bring your index data to life with our latest interactive tool. Request a demo today.', gradient: 'from-[#1e3a5f] to-[#2563eb]', btns: ['Learn More', 'Watch Demo Video'] },
  { title: 'Automate Insights to Drive Decisions', desc: 'Experience AI Portfolio Insights with modern data warehousing, intuitive dashboards, and GenAI to speed up risk analysis and empower better decisions.', gradient: 'from-[#0f766e] to-[#14b8a6]', btns: ['Read Research', 'Learn More'] },
  { title: 'GeoSpatial Asset Intelligence', desc: 'Explore physical and nature risks with our multi-award-winning solution, including PRI Award 2025 for Recognition for Action \u2014 Climate Award.', gradient: 'from-[#1e3a5f] to-[#0891b2]', btns: ['Book a demo'] },
];

const ECON_CALENDAR = [
  { date: 'Apr 25, 2026', event: 'LQ45 Index Rebalancing', tag: 'Index', tagClr: 'bg-blue-50 text-[#2563eb]' },
  { date: 'May 8, 2026', event: 'BI Rate Decision', tag: 'Macro', tagClr: 'bg-amber-50 text-amber-600' },
  { date: 'May 14, 2026', event: 'FOMC Minutes Release', tag: 'Global', tagClr: 'bg-purple-50 text-purple-600' },
  { date: 'May 15, 2026', event: 'IDX80 Semi-Annual Review', tag: 'Index', tagClr: 'bg-blue-50 text-[#2563eb]' },
  { date: 'Jun 2, 2026', event: 'Indonesia GDP Q1 2026', tag: 'Macro', tagClr: 'bg-amber-50 text-amber-600' },
  { date: 'Jun 5, 2026', event: 'Q1 Earnings Season Ends', tag: 'Earnings', tagClr: 'bg-emerald-50 text-emerald-600' },
  { date: 'Jun 12, 2026', event: 'BI Rate Decision', tag: 'Macro', tagClr: 'bg-amber-50 text-amber-600' },
];

const VISITED = [
  { cat: 'Companies', label: 'Index Composition Viewer', Icon: Building2, time: '1 day ago' },
  { cat: 'Research', label: 'All Items', Icon: BarChart3, time: '2 days ago' },
  { cat: 'Assets', label: 'Equities', Icon: LineChart, time: '3 days ago' },
];

/* ═══ PAGE ═══ */
export default function DashboardPage() {
  return (
    <div className="p-5 pb-0">
      {/* MAIN GRID */}
      <div className="grid grid-cols-[1fr_300px] gap-4">
        {/* ═══ LEFT ═══ */}
        <div className="space-y-4">
          {/* Index Cards */}
          <div className="grid grid-cols-5 gap-3">
            {IDX_SYMBOLS.map((s) => <IdxCard key={s} symbol={s} />)}
          </div>

          {/* Market Research and Insights */}
          <div className={card}>
            <div className="flex items-center justify-between border-b border-[#e2e8f0] px-5 py-3.5">
              <h2 className="text-[16px] font-semibold text-[#1e293b]">Market Research and Insights</h2>
              <Link href="/research" className="text-[14px] font-medium text-[#2563eb] hover:underline">View All</Link>
            </div>
            <div className="grid grid-cols-2">
              {ARTICLES.map((a, i) => (
                <Link key={a.id} href="/research"
                  className={`group flex gap-4 p-5 transition-colors hover:bg-[#f8fafc] ${i % 2 === 0 ? 'border-r border-[#e2e8f0]' : ''} ${i < 2 ? 'border-b border-[#e2e8f0]' : ''}`}>
                  <div className="h-[85px] w-[115px] shrink-0 rounded-lg" style={{ backgroundColor: a.bg }} />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[15px] font-bold leading-snug text-[#1e3a8a] group-hover:underline line-clamp-2">{a.title}</h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-[#64748b] line-clamp-3">{a.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* ═══ RIGHT SIDEBAR ═══ */}
        <div className="space-y-4">
          {/* Support + Discover */}
          <div className={`${card} p-4`}>
            <div className="flex gap-6">
              <div className="flex-1">
                <h3 className="mb-2 text-[14px] font-bold text-[#1e293b]">Support</h3>
                {['Release Notes', 'Submit a Support Ticket', 'View Support Tickets', 'Contact Us', 'Support Site', 'Platform Status'].map((l) => (
                  <div key={l} className="cursor-pointer py-[3px] text-[14px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
              <div className="flex-1">
                <h3 className="mb-2 text-[14px] font-bold text-[#1e293b]">Discover</h3>
                {['Datasets', 'APIs', 'Models', 'Stock Screener', 'Total Plan', 'Capital Analytics'].map((l) => (
                  <div key={l} className="cursor-pointer py-[3px] text-[14px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
            </div>
          </div>

          {/* Recently Visited */}
          <div className={`${card} p-4`}>
            <h3 className="mb-3 text-[15px] font-bold text-[#1e293b]">Recently Visited</h3>
            <div className="space-y-3.5">
              {VISITED.map((v, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <v.Icon className="h-4 w-4 shrink-0 text-[#2563eb]" />
                  <div className="min-w-0 flex-1">
                    <span className="text-[14px] font-bold text-[#1e293b]">{v.cat}</span>
                    <span className="text-[14px] text-[#64748b]"> - </span>
                    <span className="cursor-pointer text-[14px] text-[#2563eb] hover:underline">{v.label}</span>
                  </div>
                  <span className="shrink-0 text-[12px] text-[#94a3b8]">{v.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ═══ BOTTOM: Feature Cards + Economic Calendar ═══ */}
      <div className="mt-4 grid grid-cols-4 gap-4">
        {FEATURES.map((f, i) => (
          <div key={i} className={`${card} overflow-hidden flex flex-col`}>
            <div className={`h-[130px] bg-gradient-to-br ${f.gradient}`} />
            <div className="flex flex-1 flex-col p-4">
              <h3 className="text-[15px] font-bold text-[#1e293b]">{f.title}</h3>
              <p className="mt-2 flex-1 text-[13px] leading-relaxed text-[#64748b]">{f.desc}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {f.btns.map((b, j) => (
                  <span key={j} className="cursor-pointer rounded-full border border-[#2563eb] px-3.5 py-1.5 text-[13px] font-medium text-[#2563eb] transition-colors hover:bg-[#2563eb] hover:text-white">
                    {b}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}

        {/* Economic Calendar */}
        <div className={`${card} p-4 flex flex-col`}>
          <h3 className="text-[16px] font-bold text-[#2563eb]">Economic Calendar</h3>
          <div className="mt-3 flex-1 space-y-0">
            {ECON_CALENDAR.map((e, i) => (
              <div key={i} className="border-b border-[#f1f5f9] py-2.5 last:border-0">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="text-[12px] font-semibold text-[#1e293b]">{e.date}</span>
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${e.tagClr}`}>{e.tag}</span>
                </div>
                <div className="text-[13px] text-[#475569]">{e.event}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ FOOTER ═══ */}
      <div className="mt-4 py-4">
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
