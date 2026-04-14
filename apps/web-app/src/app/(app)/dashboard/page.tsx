'use client';

import Link from 'next/link';
import { Building2, LineChart, BarChart3 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

/* ═══ CARD STYLE ═══ */
const card = 'rounded-[15px] border border-[#e2e8f0] bg-white';

/* ═══ MARKET HOURS CHECK ═══ */
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

/* ═══ SVG SPARKLINE ═══ */
function SvgSpark({ pts, up }: { pts: number[]; up: boolean }) {
  if (pts.length < 2) return null;
  const mn = Math.min(...pts);
  const mx = Math.max(...pts);
  const rng = mx - mn || 1;
  const W = 80;
  const H = 32;
  const c = pts.map((p, i) => ({
    x: (i / (pts.length - 1)) * W,
    y: 2 + 28 - ((p - mn) / rng) * 28,
  }));
  const line = c.map((v, i) => `${i === 0 ? 'M' : 'L'}${v.x.toFixed(1)},${v.y.toFixed(1)}`).join(' ');
  const fill = `${line} L${W},${H} L0,${H} Z`;
  const clr = up ? '#16a34a' : '#dc2626';
  const gid = up ? 'su' : 'sd';
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="shrink-0">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={clr} stopOpacity="0.2" />
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
    <div className={`${card} px-3.5 py-3`}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase text-[#1e293b]">{symbol}</span>
        <span className="text-[10px] tabular-nums text-[#94a3b8]">{ts}</span>
      </div>
      <div className="flex items-end justify-between">
        <div>
          {isLoading ? (
            <div className="mb-1 h-5 w-20 animate-pulse rounded bg-[#e2e8f0]" />
          ) : (
            <div className="mb-0.5 text-[15px] font-semibold tabular-nums text-[#0f172a]">
              {cur.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          )}
          {isLoading ? (
            <div className="h-3 w-14 animate-pulse rounded bg-[#e2e8f0]" />
          ) : (
            <span className={`inline-flex items-center gap-0.5 text-[11px] font-medium tabular-nums ${up ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
              {up ? '▲' : '▼'} {up ? '+' : ''}{chg.toFixed(2)}%
            </span>
          )}
        </div>
        {pts.length >= 2 && <SvgSpark pts={pts} up={up} />}
      </div>
    </div>
  );
}

/* ═══ DATA ═══ */
const IDX_SYMBOLS = ['IHSG', 'LQ45', 'IDX30', 'IDX80', 'JII'];

const ARTICLES = [
  { id: 'lq45', title: 'LQ45 Rebalancing Preview: Projected Additions and Removals', desc: 'Analysis of liquidity and market cap changes that may drive the upcoming LQ45 semi-annual review, with projected constituent changes.', bg: '#1e3a5f' },
  { id: 'bi', title: 'BI Rate Hold at 5.75%: Implications for Banking Sector Valuations', desc: 'Bank Indonesia maintained its benchmark rate for the fourth consecutive meeting. We examine the impact on net interest margins across IDX-listed banks.', bg: '#2d4a3e' },
  { id: 'mom', title: 'IDX Momentum Factor: Q1 2026 Performance Attribution', desc: 'The momentum factor delivered +3.2% alpha over the quarter, primarily driven by energy and financial sector exposure. Detailed factor decomposition inside.', bg: '#3d2e5c' },
  { id: 'idr', title: 'Rupiah Stability and Foreign Fund Flows: Q1 2026 in Review', desc: 'Foreign investors recorded net outflows of IDR 12.8T in Q1, yet the rupiah remained stable supported by strong trade surplus and BI intervention.', bg: '#4a3328' },
];

const NEWS = [
  { title: 'IHSG closes above 7,200 on banking sector strength', time: '15:02' },
  { title: 'Bank Indonesia maintains benchmark rate at 5.75%', time: '14:30' },
  { title: 'BREN surges 4.8% on renewable energy policy announcement', time: '13:45' },
  { title: 'Foreign investors net buyers for third consecutive session', time: '11:20' },
  { title: 'Rupiah strengthens to 15,420 against US dollar', time: '10:05' },
  { title: 'IDX plans new derivatives products for Q3 2026 launch', time: '09:15' },
];

const CALENDAR = [
  { date: 'Apr 25', event: 'LQ45 Index Rebalancing', type: 'Index' },
  { date: 'May 8', event: 'BI Rate Decision', type: 'Macro' },
  { date: 'May 15', event: 'IDX80 Semi-Annual Review', type: 'Index' },
  { date: 'Jun 2', event: 'Q1 2026 Earnings Season Ends', type: 'Earnings' },
];

const RATES: { label: string; value: string; delta: string; type: 'positive' | 'negative' | 'neutral' }[] = [
  { label: 'USD/IDR', value: '15,420', delta: '+0.3%', type: 'positive' },
  { label: 'BI Rate', value: '5.75%', delta: 'Hold', type: 'neutral' },
  { label: '10Y Govt Bond', value: '6.82%', delta: '-2bps', type: 'positive' },
  { label: 'Inflation (YoY)', value: '2.8%', delta: 'Feb 2026', type: 'neutral' },
  { label: 'Trade Balance', value: '+$3.2B', delta: 'Feb 2026', type: 'neutral' },
  { label: 'FX Reserves', value: '$139.4B', delta: 'Mar 2026', type: 'neutral' },
];

const ACTIONS = [
  { date: 'Apr 18', sym: 'BBCA', act: 'Cash Dividend', detail: 'IDR 180/share' },
  { date: 'Apr 22', sym: 'BMRI', act: 'Rights Issue', detail: '1:4 ratio' },
  { date: 'Apr 25', sym: '—', act: 'LQ45 Rebalancing', detail: 'Effective date' },
  { date: 'May 2', sym: 'TLKM', act: 'Cash Dividend', detail: 'IDR 95/share' },
  { date: 'May 15', sym: '—', act: 'IDX80 Review', detail: 'Semi-annual' },
];

const VISITED = [
  { cat: 'Companies', label: 'Index Composition Viewer', Icon: Building2, time: 'Today' },
  { cat: 'Research', label: 'All Items', Icon: BarChart3, time: '1 day ago' },
  { cat: 'Assets', label: 'Equities', Icon: LineChart, time: '1 day ago' },
];

/* ═══ PAGE ═══ */
export default function DashboardPage() {
  return (
    <div className="p-5 pb-0">
      <div className="grid grid-cols-[1fr_300px] gap-4">
        {/* ═══ LEFT ═══ */}
        <div className="space-y-4">
          <div className="grid grid-cols-5 gap-3">
            {IDX_SYMBOLS.map((s) => <IdxCard key={s} symbol={s} />)}
          </div>

          <div className={card}>
            <div className="flex items-center justify-between border-b border-[#e2e8f0] px-5 py-3">
              <h2 className="text-[14px] font-semibold text-[#1e293b]">Market Research and Insights</h2>
              <Link href="/research" className="text-[12px] font-medium text-[#2563eb] hover:underline">View All</Link>
            </div>
            <div className="grid grid-cols-2">
              {ARTICLES.map((a, i) => (
                <Link key={a.id} href="/research"
                  className={`group flex gap-4 p-5 transition-colors hover:bg-[#f8fafc] ${i % 2 === 0 ? 'border-r border-[#e2e8f0]' : ''} ${i < 2 ? 'border-b border-[#e2e8f0]' : ''}`}>
                  <div className="h-[72px] w-[100px] shrink-0 rounded-lg" style={{ backgroundColor: a.bg }} />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[13px] font-bold leading-snug text-[#1e3a8a] group-hover:underline line-clamp-2">{a.title}</h3>
                    <p className="mt-1 text-[11px] leading-relaxed text-[#64748b] line-clamp-3">{a.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* ═══ RIGHT ═══ */}
        <div className="space-y-4">
          <div className={`${card} p-4`}>
            <div className="flex gap-6">
              <div className="flex-1">
                <h3 className="mb-2 text-[12px] font-bold text-[#1e293b]">Support</h3>
                {['Release Notes', 'Submit a Support Ticket', 'View Support Tickets', 'Contact Us', 'Support Site', 'Platform Status'].map((l) => (
                  <div key={l} className="cursor-pointer py-[2px] text-[12px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
              <div className="flex-1">
                <h3 className="mb-2 text-[12px] font-bold text-[#1e293b]">Discover</h3>
                {['Datasets', 'APIs', 'Models', 'Stock Screener', 'Total Plan', 'Capital Analytics'].map((l) => (
                  <div key={l} className="cursor-pointer py-[2px] text-[12px] text-[#2563eb] hover:underline">{l}</div>
                ))}
              </div>
            </div>
          </div>

          <div className={`${card} p-4`}>
            <h3 className="mb-3 text-[12px] font-bold text-[#1e293b]">Recently Visited</h3>
            <div className="space-y-3">
              {VISITED.map((v, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <v.Icon className="h-4 w-4 shrink-0 text-[#2563eb]" />
                  <div className="min-w-0 flex-1">
                    <span className="text-[11px] font-semibold text-[#1e293b]">{v.cat}</span>
                    <span className="text-[11px] text-[#64748b]"> - </span>
                    <span className="cursor-pointer text-[11px] text-[#2563eb] hover:underline">{v.label}</span>
                  </div>
                  <span className="shrink-0 text-[10px] text-[#94a3b8]">{v.time}</span>
                </div>
              ))}
            </div>
          </div>

          <div className={`${card} p-4`}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[12px] font-bold text-[#1e293b]">News &amp; Updates</h3>
              <span className="cursor-pointer text-[11px] text-[#2563eb] hover:underline">View All</span>
            </div>
            {NEWS.map((n, i) => (
              <div key={i} className="flex gap-2.5 border-b border-[#f1f5f9] py-2.5 last:border-0">
                <span className="w-[34px] shrink-0 text-[10px] tabular-nums text-[#94a3b8]">{n.time}</span>
                <span className="text-[11px] leading-snug text-[#475569]">{n.title}</span>
              </div>
            ))}
          </div>

          <div className={`${card} p-4`}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[12px] font-bold text-[#1e293b]">IDX Calendar</h3>
              <span className="cursor-pointer text-[11px] text-[#2563eb] hover:underline">View All</span>
            </div>
            {CALENDAR.map((c, i) => (
              <div key={i} className="border-b border-[#f1f5f9] py-2.5 last:border-0">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="text-[10px] font-semibold text-[#1e293b]">{c.date}</span>
                  <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-medium ${c.type === 'Index' ? 'bg-blue-50 text-[#2563eb]' : c.type === 'Macro' ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'}`}>{c.type}</span>
                </div>
                <div className="text-[11px] text-[#475569]">{c.event}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ BOTTOM ═══ */}
      <div className="mt-4 grid grid-cols-3 gap-4">
        <div className={`${card} p-5`}>
          <h2 className="mb-3 text-[13px] font-bold text-[#1e293b]">Market Summary</h2>
          <p className="text-[12px] leading-relaxed text-[#475569]">
            IHSG closed at 7,234.56 (+0.45%), led by strength in the financials sector as banking
            stocks extended gains following Bank Indonesia&apos;s decision to hold rates at 5.75%.
            Foreign investors were net buyers for the third consecutive session, adding IDR 842B.
          </p>
          <div className="mt-3 space-y-1.5">
            {[
              { clr: '#16a34a', text: 'Financials +1.2% — BBCA, BMRI led gains' },
              { clr: '#dc2626', text: 'Technology -1.8% — GOTO on earnings concern' },
              { clr: '#16a34a', text: 'Foreign net buy: +IDR 842B (3rd day)' },
              { clr: '#16a34a', text: 'Rupiah: 15,420/USD (+0.3%)' },
            ].map((b, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: b.clr }} />
                <span className="text-[#475569]">{b.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className={`${card} p-5`}>
          <h2 className="mb-3 text-[13px] font-bold text-[#1e293b]">Rupiah &amp; Rates</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            {RATES.map((r) => (
              <div key={r.label}>
                <div className="mb-0.5 text-[10px] font-medium text-[#94a3b8]">{r.label}</div>
                <div className="text-[15px] font-semibold tabular-nums text-[#0f172a]">{r.value}</div>
                <div className={`mt-0.5 text-[10px] font-medium tabular-nums ${r.type === 'positive' ? 'text-[#16a34a]' : r.type === 'negative' ? 'text-[#dc2626]' : 'text-[#94a3b8]'}`}>{r.delta}</div>
              </div>
            ))}
          </div>
        </div>

        <div className={`${card} p-5`}>
          <h2 className="mb-3 text-[13px] font-bold text-[#1e293b]">IPO &amp; Corporate Actions</h2>
          {ACTIONS.map((a, i) => (
            <div key={i} className="flex items-start gap-3 border-b border-[#f1f5f9] py-2.5 last:border-0">
              <span className="w-[44px] shrink-0 text-[11px] tabular-nums text-[#94a3b8]">{a.date}</span>
              <span className="w-[40px] shrink-0 text-[11px] font-bold text-[#2563eb]">{a.sym}</span>
              <div className="flex-1">
                <div className="text-[12px] text-[#1e293b]">{a.act}</div>
                <div className="text-[10px] text-[#94a3b8]">{a.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 py-4">
        <p className="text-center text-[10px] text-[#94a3b8]">
          &copy; 2026 Pyhron Inc. All Rights Reserved. Subject to{' '}
          <span className="cursor-pointer underline">Terms of Use</span> &amp;{' '}
          <span className="cursor-pointer underline">Disclaimer</span>.{' '}
          <span className="cursor-pointer underline">Manage Cookies</span>.
        </p>
      </div>
    </div>
  );
}
