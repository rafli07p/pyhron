'use client';

import Link from 'next/link';
import { Building2, LineChart, BarChart3 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

const INDEX_SYMBOLS = ['IHSG', 'LQ45', 'IDX30', 'IDX80', 'JII'];

/* ═══ INTRADAY HOOK (inlined to avoid Turbopack name collision) ═══ */
interface IntradayData {
  symbol: string;
  current: number;
  open: number;
  change: number;
  points: number[];
  timestamps: string[];
  lastUpdate: string;
}

function isIDXMarketOpen(): boolean {
  const now = new Date();
  const wibHour = (now.getUTCHours() + 7) % 24;
  const wibMinute = now.getUTCMinutes();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const t = wibHour * 60 + wibMinute;
  return (t >= 540 && t <= 690) || (t >= 810 && t <= 910);
}

function useIntradayData(symbol: string) {
  return useQuery<IntradayData>({
    queryKey: ['intraday', symbol],
    queryFn: async () => {
      const res = await fetch(`/api/v1/markets/intraday/${encodeURIComponent(symbol)}`);
      if (!res.ok) throw new Error('Intraday fetch failed');
      return res.json() as Promise<IntradayData>;
    },
    refetchInterval: isIDXMarketOpen() ? 30_000 : false,
    staleTime: 15_000,
    enabled: !!symbol,
  });
}

/* ═══ SPARKLINE (inlined) ═══ */
function Sparkline({ points, positive, width = 80, height = 32 }: { points: number[]; positive: boolean; width?: number; height?: number }) {
  if (points.length < 2) return null;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const pad = 2;
  const chartH = height - pad * 2;
  const coords = points.map((p, i) => {
    const x = (i / (points.length - 1)) * width;
    const y = pad + chartH - ((p - min) / range) * chartH;
    return { x, y };
  });
  const linePath = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const fillPath = `${linePath} L${width},${height} L0,${height} Z`;
  const color = positive ? '#16a34a' : '#dc2626';
  const gradId = `spark-${positive ? 'up' : 'dn'}`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="shrink-0">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fillPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ═══ RESEARCH ARTICLES ═══ */
const RESEARCH_ARTICLES = [
  {
    id: 'lq45-rebalancing',
    title: 'LQ45 Rebalancing Preview: Projected Additions and Removals',
    description: 'Analysis of liquidity and market cap changes that may drive the upcoming LQ45 semi-annual review, with projected constituent changes.',
    color: '#1e3a5f',
  },
  {
    id: 'bi-rate',
    title: 'BI Rate Hold at 5.75%: Implications for Banking Sector Valuations',
    description: 'Bank Indonesia maintained its benchmark rate for the fourth consecutive meeting. We examine the impact on net interest margins across IDX-listed banks.',
    color: '#2d4a3e',
  },
  {
    id: 'momentum-factor',
    title: 'IDX Momentum Factor: Q1 2026 Performance Attribution',
    description: 'The momentum factor delivered +3.2% alpha over the quarter, primarily driven by energy and financial sector exposure. Detailed factor decomposition inside.',
    color: '#3d2e5c',
  },
  {
    id: 'rupiah-flows',
    title: 'Rupiah Stability and Foreign Fund Flows: Q1 2026 in Review',
    description: 'Foreign investors recorded net outflows of IDR 12.8T in Q1, yet the rupiah remained stable supported by strong trade surplus and BI intervention.',
    color: '#4a3328',
  },
];

/* ═══ NEWS ═══ */
const NEWS = [
  { title: 'IHSG closes above 7,200 on banking sector strength', time: '15:02' },
  { title: 'Bank Indonesia maintains benchmark rate at 5.75%', time: '14:30' },
  { title: 'BREN surges 4.8% on renewable energy policy announcement', time: '13:45' },
  { title: 'Foreign investors net buyers for third consecutive session', time: '11:20' },
  { title: 'Rupiah strengthens to 15,420 against US dollar', time: '10:05' },
  { title: 'IDX plans new derivatives products for Q3 2026 launch', time: '09:15' },
];

/* ═══ CALENDAR ═══ */
const CALENDAR = [
  { date: 'Apr 25', event: 'LQ45 Index Rebalancing', type: 'Index' },
  { date: 'May 8', event: 'BI Rate Decision', type: 'Macro' },
  { date: 'May 15', event: 'IDX80 Semi-Annual Review', type: 'Index' },
  { date: 'Jun 2', event: 'Q1 2026 Earnings Season Ends', type: 'Earnings' },
];

/* ═══ RATES ═══ */
const RATES: { label: string; value: string; delta: string; type: 'positive' | 'negative' | 'neutral' }[] = [
  { label: 'USD/IDR', value: '15,420', delta: '+0.3%', type: 'positive' },
  { label: 'BI Rate', value: '5.75%', delta: 'Hold', type: 'neutral' },
  { label: '10Y Govt Bond', value: '6.82%', delta: '-2bps', type: 'positive' },
  { label: 'Inflation (YoY)', value: '2.8%', delta: 'Feb 2026', type: 'neutral' },
  { label: 'Trade Balance', value: '+$3.2B', delta: 'Feb 2026', type: 'neutral' },
  { label: 'FX Reserves', value: '$139.4B', delta: 'Mar 2026', type: 'neutral' },
];

/* ═══ CORPORATE ACTIONS ═══ */
const CORP_ACTIONS = [
  { date: 'Apr 18', symbol: 'BBCA', action: 'Cash Dividend', detail: 'IDR 180/share' },
  { date: 'Apr 22', symbol: 'BMRI', action: 'Rights Issue', detail: '1:4 ratio' },
  { date: 'Apr 25', symbol: '—', action: 'LQ45 Rebalancing', detail: 'Effective date' },
  { date: 'May 2', symbol: 'TLKM', action: 'Cash Dividend', detail: 'IDR 95/share' },
  { date: 'May 15', symbol: '—', action: 'IDX80 Review', detail: 'Semi-annual' },
];

/* ═══ RECENTLY VISITED ═══ */
const RECENTLY_VISITED = [
  { category: 'Companies', label: 'Index Composition Viewer', icon: Building2, time: 'Today' },
  { category: 'Research', label: 'All Items', icon: BarChart3, time: '1 day ago' },
  { category: 'Assets', label: 'Equities', icon: LineChart, time: '1 day ago' },
];

/* ═══ INDEX CARD ═══ */
function IndexCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useIntradayData(symbol);

  const current = data?.current ?? 0;
  const change = data?.change ?? 0;
  const points = data?.points ?? [];
  const lastUpdate = data?.lastUpdate ?? '--:--';
  const positive = change >= 0;

  return (
    <div className={`${card} px-3.5 py-3`}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase text-[#1e293b]">{symbol}</span>
        <span className="text-[10px] tabular-nums text-[#94a3b8]">{lastUpdate}</span>
      </div>
      <div className="flex items-end justify-between">
        <div>
          {isLoading ? (
            <div className="mb-1 h-5 w-20 animate-pulse rounded bg-[#e2e8f0]" />
          ) : (
            <div className="mb-0.5 text-[15px] font-semibold tabular-nums text-[#0f172a]">
              {current.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          )}
          {isLoading ? (
            <div className="h-3 w-14 animate-pulse rounded bg-[#e2e8f0]" />
          ) : (
            <span className={`inline-flex items-center gap-0.5 text-[11px] font-medium tabular-nums ${positive ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
              {positive ? '▲' : '▼'} {positive ? '+' : ''}{change.toFixed(2)}%
            </span>
          )}
        </div>
        {points.length >= 2 && (
          <Sparkline points={points} positive={positive} width={80} height={32} />
        )}
      </div>
    </div>
  );
}

/* ═══ CARD WRAPPER ═══ */
const card = 'rounded-[15px] border border-[#e2e8f0] bg-white';

/* ═══ PAGE ═══ */
export default function DashboardPage() {
  return (
    <div className="p-5 pb-0">
      {/* MAIN GRID: left content + right sidebar */}
      <div className="grid grid-cols-[1fr_300px] gap-4">

        {/* ═══ LEFT COLUMN ═══ */}
        <div className="space-y-4">
          {/* Index Cards Row */}
          <div className="grid grid-cols-5 gap-3">
            {INDEX_SYMBOLS.map((symbol) => (
              <IndexCard key={symbol} symbol={symbol} />
            ))}
          </div>

          {/* Market Research and Insights */}
          <div className={card}>
            <div className="flex items-center justify-between border-b border-[#e2e8f0] px-5 py-3">
              <h2 className="text-[14px] font-semibold text-[#1e293b]">Market Research and Insights</h2>
              <Link href="/research" className="text-[12px] font-medium text-[#2563eb] hover:underline">View All</Link>
            </div>
            <div className="grid grid-cols-2">
              {RESEARCH_ARTICLES.map((article, i) => (
                <Link
                  key={article.id}
                  href="/research"
                  className={`group flex gap-4 p-5 transition-colors hover:bg-[#f8fafc] ${i % 2 === 0 ? 'border-r border-[#e2e8f0]' : ''} ${i < 2 ? 'border-b border-[#e2e8f0]' : ''}`}
                >
                  <div className="h-[72px] w-[100px] shrink-0 rounded-lg" style={{ backgroundColor: article.color }} />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[13px] font-bold leading-snug text-[#1e3a8a] group-hover:underline line-clamp-2">
                      {article.title}
                    </h3>
                    <p className="mt-1 text-[11px] leading-relaxed text-[#64748b] line-clamp-3">
                      {article.description}
                    </p>
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
                <h3 className="mb-2 text-[12px] font-bold text-[#1e293b]">Support</h3>
                {['Release Notes', 'Submit a Support Ticket', 'View Support Tickets', 'Contact Us', 'Support Site', 'Platform Status'].map((label) => (
                  <div key={label} className="py-[2px] text-[12px] text-[#2563eb] hover:underline cursor-pointer">{label}</div>
                ))}
              </div>
              <div className="flex-1">
                <h3 className="mb-2 text-[12px] font-bold text-[#1e293b]">Discover</h3>
                {['Datasets', 'APIs', 'Models', 'Stock Screener', 'Total Plan', 'Capital Analytics'].map((label) => (
                  <div key={label} className="py-[2px] text-[12px] text-[#2563eb] hover:underline cursor-pointer">{label}</div>
                ))}
              </div>
            </div>
          </div>

          {/* Recently Visited */}
          <div className={`${card} p-4`}>
            <h3 className="mb-3 text-[12px] font-bold text-[#1e293b]">Recently Visited</h3>
            <div className="space-y-3">
              {RECENTLY_VISITED.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4 shrink-0 text-[#2563eb]" />
                    <div className="min-w-0 flex-1">
                      <span className="text-[11px] font-semibold text-[#1e293b]">{item.category}</span>
                      <span className="text-[11px] text-[#64748b]"> - </span>
                      <span className="text-[11px] text-[#2563eb] hover:underline cursor-pointer">{item.label}</span>
                    </div>
                    <span className="shrink-0 text-[10px] text-[#94a3b8]">{item.time}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* News & Updates */}
          <div className={`${card} p-4`}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[12px] font-bold text-[#1e293b]">News &amp; Updates</h3>
              <span className="text-[11px] text-[#2563eb] hover:underline cursor-pointer">View All</span>
            </div>
            <div className="space-y-0">
              {NEWS.map((item, i) => (
                <div key={i} className="flex gap-2.5 border-b border-[#f1f5f9] py-2.5 last:border-0">
                  <span className="w-[34px] shrink-0 text-[10px] tabular-nums text-[#94a3b8]">{item.time}</span>
                  <span className="text-[11px] leading-snug text-[#475569]">{item.title}</span>
                </div>
              ))}
            </div>
          </div>

          {/* IDX Calendar */}
          <div className={`${card} p-4`}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[12px] font-bold text-[#1e293b]">IDX Calendar</h3>
              <span className="text-[11px] text-[#2563eb] hover:underline cursor-pointer">View All</span>
            </div>
            <div className="space-y-0">
              {CALENDAR.map((item, i) => (
                <div key={i} className="border-b border-[#f1f5f9] py-2.5 last:border-0">
                  <div className="mb-0.5 flex items-center gap-2">
                    <span className="text-[10px] font-semibold text-[#1e293b]">{item.date}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                      item.type === 'Index' ? 'bg-blue-50 text-[#2563eb]' :
                      item.type === 'Macro' ? 'bg-amber-50 text-amber-600' :
                      'bg-emerald-50 text-emerald-600'
                    }`}>{item.type}</span>
                  </div>
                  <div className="text-[11px] text-[#475569]">{item.event}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ═══ BOTTOM ROW — full width ═══ */}
      <div className="mt-4 grid grid-cols-3 gap-4">
        {/* Market Summary */}
        <div className={`${card} p-5`}>
          <h2 className="mb-3 text-[13px] font-bold text-[#1e293b]">Market Summary</h2>
          <p className="text-[12px] leading-relaxed text-[#475569]">
            IHSG closed at 7,234.56 (+0.45%), led by strength in the financials sector as banking
            stocks extended gains following Bank Indonesia&apos;s decision to hold rates at 5.75%.
            Foreign investors were net buyers for the third consecutive session, adding IDR 842B.
          </p>
          <div className="mt-3 space-y-1.5">
            <div className="flex items-center gap-2 text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#16a34a]" />
              <span className="text-[#475569]">Financials +1.2% — BBCA, BMRI led gains</span>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#dc2626]" />
              <span className="text-[#475569]">Technology -1.8% — GOTO on earnings concern</span>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#16a34a]" />
              <span className="text-[#475569]">Foreign net buy: +IDR 842B (3rd day)</span>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#16a34a]" />
              <span className="text-[#475569]">Rupiah: 15,420/USD (+0.3%)</span>
            </div>
          </div>
        </div>

        {/* Rupiah & Rates */}
        <div className={`${card} p-5`}>
          <h2 className="mb-3 text-[13px] font-bold text-[#1e293b]">Rupiah &amp; Rates</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            {RATES.map((item) => (
              <div key={item.label}>
                <div className="mb-0.5 text-[10px] font-medium text-[#94a3b8]">{item.label}</div>
                <div className="text-[15px] font-semibold tabular-nums text-[#0f172a]">{item.value}</div>
                <div className={`mt-0.5 text-[10px] font-medium tabular-nums ${
                  item.type === 'positive' ? 'text-[#16a34a]' :
                  item.type === 'negative' ? 'text-[#dc2626]' :
                  'text-[#94a3b8]'
                }`}>{item.delta}</div>
              </div>
            ))}
          </div>
        </div>

        {/* IPO & Corporate Actions */}
        <div className={`${card} p-5`}>
          <h2 className="mb-3 text-[13px] font-bold text-[#1e293b]">IPO &amp; Corporate Actions</h2>
          <div className="space-y-0">
            {CORP_ACTIONS.map((item, i) => (
              <div key={i} className="flex items-start gap-3 border-b border-[#f1f5f9] py-2.5 last:border-0">
                <span className="w-[44px] shrink-0 text-[11px] tabular-nums text-[#94a3b8]">{item.date}</span>
                <span className="w-[40px] shrink-0 text-[11px] font-bold text-[#2563eb]">{item.symbol}</span>
                <div className="flex-1">
                  <div className="text-[12px] text-[#1e293b]">{item.action}</div>
                  <div className="text-[10px] text-[#94a3b8]">{item.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ FOOTER ═══ */}
      <div className="py-4 mt-4">
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
