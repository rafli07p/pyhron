'use client';

import Link from 'next/link';

/* ═══ INDEX DATA ═══ */
const INDICES = [
  { symbol: 'IHSG', name: 'Composite', value: 7234.56, change: -0.53, sparkline: [7180,7195,7210,7190,7220,7235,7215,7240,7234,7250,7245,7230,7234] },
  { symbol: 'LQ45', name: 'LQ45', value: 985.23, change: -0.52, sparkline: [990,988,985,982,986,984,988,985,983,987,985,984,985] },
  { symbol: 'IDX30', name: 'IDX30', value: 482.18, change: 0.58, sparkline: [478,479,480,479,481,480,482,481,483,482,484,483,482] },
  { symbol: 'IDX80', name: 'IDX80', value: 132.45, change: 0.66, sparkline: [130,131,131,132,131,132,131,132,133,132,133,132,132] },
  { symbol: 'JII', name: 'JII', value: 548.92, change: -0.58, sparkline: [552,551,550,551,549,550,548,549,547,548,549,548,548] },
];

/* ═══ RESEARCH ARTICLES ═══ */
const RESEARCH_ARTICLES = [
  {
    id: 'lq45-rebalancing',
    category: 'Index Research',
    title: 'LQ45 Rebalancing Preview: Projected Additions and Removals',
    description: 'Analysis of liquidity and market cap changes that may drive the upcoming LQ45 semi-annual review, with projected constituent changes.',
    date: 'Apr 10, 2026',
    color: '#1e3a5f',
    href: '/research',
  },
  {
    id: 'bi-rate',
    category: 'Macro & Rates',
    title: 'BI Rate Hold at 5.75%: Implications for Banking Sector Valuations',
    description: 'Bank Indonesia maintained its benchmark rate for the fourth consecutive meeting. We examine the impact on net interest margins across IDX-listed banks.',
    date: 'Apr 8, 2026',
    color: '#2d4a3e',
    href: '/research',
  },
  {
    id: 'momentum-factor',
    category: 'Quantitative Research',
    title: 'IDX Momentum Factor: Q1 2026 Performance Attribution',
    description: 'The momentum factor delivered +3.2% alpha over the quarter, primarily driven by energy and financial sector exposure. Detailed factor decomposition inside.',
    date: 'Apr 5, 2026',
    color: '#3d2e5c',
    href: '/research',
  },
  {
    id: 'rupiah-flows',
    category: 'Market Commentary',
    title: 'Rupiah Stability and Foreign Fund Flows: Q1 2026 in Review',
    description: 'Foreign investors recorded net outflows of IDR 12.8T in Q1, yet the rupiah remained stable supported by strong trade surplus and BI intervention.',
    date: 'Apr 2, 2026',
    color: '#4a3328',
    href: '/research',
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
  { date: 'Apr 25, 2026', event: 'LQ45 Index Rebalancing', type: 'Index' },
  { date: 'May 8, 2026', event: 'BI Rate Decision', type: 'Macro' },
  { date: 'May 15, 2026', event: 'IDX80 Semi-Annual Review', type: 'Index' },
  { date: 'Jun 2, 2026', event: 'Q1 2026 Earnings Season Ends', type: 'Earnings' },
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

/* ═══ SPARKLINE COMPONENT ═══ */
function Sparkline({ data, positive }: { data: number[]; positive: boolean }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * 60;
      const y = 24 - ((v - min) / (max - min || 1)) * 24;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg viewBox="0 0 60 24" className="h-[24px] w-[60px]">
      <polyline
        points={points}
        fill="none"
        stroke={positive ? '#34d399' : '#f87171'}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ═══ PAGE ═══ */
export default function DashboardPage() {
  return (
    <div className="grid h-[calc(100dvh-48px)] grid-cols-[1fr_320px] gap-4 overflow-y-auto p-5">
      {/* ═══ LEFT COLUMN ═══ */}
      <div className="space-y-4">
        {/* Index Cards */}
        <div className="grid grid-cols-5 gap-3">
          {INDICES.map((idx) => (
            <div key={idx.symbol} className="rounded-lg border border-[#1e1e22] bg-[#111113] p-3.5">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[11px] font-medium tracking-wide text-white/80">{idx.symbol}</span>
                <span className="text-[10px] text-white/25">15:00</span>
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <div
                    className="mb-1 font-mono text-[18px] font-semibold leading-none text-white"
                    style={{ fontVariantNumeric: 'tabular-nums' }}
                  >
                    {idx.value.toLocaleString('id-ID', { minimumFractionDigits: 2 })}
                  </div>
                  <span
                    className={`font-mono text-[12px] font-medium ${
                      idx.change >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {idx.change >= 0 ? '▲' : '▼'} {Math.abs(idx.change).toFixed(2)}%
                  </span>
                </div>
                <Sparkline data={idx.sparkline} positive={idx.change >= 0} />
              </div>
            </div>
          ))}
        </div>

        {/* Research Section */}
        <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-5">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-[13px] font-semibold tracking-wide text-white/70">
              Market Research and Insights
            </h2>
            <Link
              href="/research"
              className="text-[12px] text-[#5b8def] transition-colors hover:text-[#7ba4f7]"
            >
              View All
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {RESEARCH_ARTICLES.map((article) => (
              <Link
                key={article.id}
                href={article.href}
                className="group block overflow-hidden rounded-lg border border-[#1e1e22] transition-colors hover:border-[#2a2a30]"
              >
                <div className="relative h-[110px]" style={{ backgroundColor: article.color }}>
                  <span className="absolute bottom-2 left-3 text-[10px] font-medium tracking-wide text-white/50">
                    {article.category}
                  </span>
                </div>
                <div className="p-3.5">
                  <h3 className="mb-2 line-clamp-2 text-[13px] font-semibold leading-snug text-white/85 transition-colors group-hover:text-white">
                    {article.title}
                  </h3>
                  <p className="line-clamp-2 text-[11px] leading-relaxed text-white/30">
                    {article.description}
                  </p>
                  <span className="mt-2 block text-[10px] text-white/15">{article.date}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-3 gap-4">
          {/* Market Summary */}
          <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-4">
            <h2 className="mb-4 text-[13px] font-semibold tracking-wide text-white/70">
              Market Summary
            </h2>
            <p className="text-[12px] leading-relaxed text-white/40">
              IHSG closed at 7,234.56 (+0.45%), led by strength in the financials sector as banking
              stocks extended gains following Bank Indonesia&apos;s decision to hold rates at 5.75%.
              Foreign investors were net buyers for the third consecutive session, adding IDR 842B.
            </p>
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-emerald-400">●</span>
                <span className="text-white/40">Financials +1.2% — BBCA, BMRI led gains</span>
              </div>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-red-400">●</span>
                <span className="text-white/40">Technology -1.8% — GOTO on earnings concern</span>
              </div>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-emerald-400">●</span>
                <span className="text-white/40">Foreign net buy: +IDR 842B (3rd day)</span>
              </div>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-emerald-400">●</span>
                <span className="text-white/40">Rupiah: 15,420/USD (+0.3%)</span>
              </div>
            </div>
          </div>

          {/* Rupiah & Rates */}
          <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-4">
            <h2 className="mb-4 text-[13px] font-semibold tracking-wide text-white/70">
              Rupiah &amp; Rates
            </h2>
            <div className="grid grid-cols-2 gap-x-6 gap-y-5">
              {RATES.map((item) => (
                <div key={item.label}>
                  <div className="mb-1 text-[10px] text-white/25">{item.label}</div>
                  <div
                    className="font-mono text-[15px] font-semibold text-white/90"
                    style={{ fontVariantNumeric: 'tabular-nums' }}
                  >
                    {item.value}
                  </div>
                  <div
                    className={`mt-0.5 font-mono text-[10px] ${
                      item.type === 'positive'
                        ? 'text-emerald-400'
                        : item.type === 'negative'
                          ? 'text-red-400'
                          : 'text-white/20'
                    }`}
                  >
                    {item.delta}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* IPO & Corporate Actions */}
          <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-4">
            <h2 className="mb-4 text-[13px] font-semibold tracking-wide text-white/70">
              IPO &amp; Corporate Actions
            </h2>
            <div className="space-y-0">
              {CORP_ACTIONS.map((item, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 border-b border-[#1e1e22] py-2.5 last:border-0"
                >
                  <span className="w-[48px] shrink-0 font-mono text-[11px] text-white/25">
                    {item.date}
                  </span>
                  <span className="w-[40px] shrink-0 font-mono text-[11px] font-semibold text-[#5b8def]">
                    {item.symbol}
                  </span>
                  <div className="flex-1">
                    <div className="text-[12px] text-white/60">{item.action}</div>
                    <div className="text-[10px] text-white/25">{item.detail}</div>
                  </div>
                </div>
              ))}
            </div>
            <Link
              href="/data/catalog"
              className="mt-3 block text-[11px] text-[#5b8def] transition-colors hover:text-[#7ba4f7]"
            >
              View all corporate actions →
            </Link>
          </div>
        </div>
      </div>

      {/* ═══ RIGHT SIDEBAR ═══ */}
      <div className="space-y-4">
        {/* News & Updates */}
        <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[13px] font-semibold tracking-wide text-white/70">
              News &amp; Updates
            </h2>
            <Link
              href="/research"
              className="text-[11px] text-[#5b8def] transition-colors hover:text-[#7ba4f7]"
            >
              View All
            </Link>
          </div>
          <div className="space-y-0">
            {NEWS.map((item, i) => (
              <Link
                key={i}
                href="/research"
                className="group flex gap-3 border-b border-[#1e1e22] py-3 transition-colors last:border-0 hover:bg-white/[0.01]"
              >
                <span className="w-[36px] shrink-0 pt-0.5 font-mono text-[10px] text-white/15">
                  {item.time}
                </span>
                <span className="text-[12px] leading-snug text-white/50 transition-colors group-hover:text-white/70">
                  {item.title}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* IDX Calendar */}
        <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[13px] font-semibold tracking-wide text-white/70">IDX Calendar</h2>
            <Link
              href="/data/catalog"
              className="text-[11px] text-[#5b8def] transition-colors hover:text-[#7ba4f7]"
            >
              View All
            </Link>
          </div>
          <div className="space-y-0">
            {CALENDAR.map((item, i) => (
              <div key={i} className="border-b border-[#1e1e22] py-3 last:border-0">
                <div className="mb-1 flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-medium tracking-wide ${
                      item.type === 'Index'
                        ? 'bg-[#5b8def]/10 text-[#5b8def]'
                        : item.type === 'Macro'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-emerald-500/10 text-emerald-400'
                    }`}
                  >
                    {item.type}
                  </span>
                  <span className="text-[10px] text-white/20">{item.date}</span>
                </div>
                <div className="text-[12px] text-white/55">{item.event}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
