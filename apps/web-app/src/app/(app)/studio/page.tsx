'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { CandlestickChart, CandlestickChartSkeleton, type OHLCV } from '@/design-system/charts/CandlestickChart';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';
import { generateOHLCV, generateScreenerData } from '@/mocks/terminal-data';
import { useQuote, useOHLCV, useScreener } from '@/hooks/use-market-data';

// ── Tabs ──
const TABS = ['Workbench', 'Dashboards', 'Screener'] as const;
type Tab = (typeof TABS)[number];

// ── Sidebar metric sections ──
const METRIC_SECTIONS: { label: string; items: string[] }[] = [
  { label: 'Price & Volume', items: ['OHLCV', 'Volume', 'VWAP'] },
  { label: 'Technical', items: ['RSI(14)', 'SMA(20)', 'SMA(50)', 'SMA(200)', 'EMA', 'MACD', 'Bollinger', 'ATR'] },
  { label: 'Fundamentals', items: ['P/E', 'P/B', 'Div Yield', 'EPS', 'ROE'] },
  { label: 'Factor Scores', items: ['Momentum', 'Value', 'Quality', 'Size'] },
];

const TIME_RANGES = ['1D', '1W', '1M', '3M', '1Y'] as const;

const SCREENER_COLS = [
  { key: 'symbol', label: 'Symbol' },
  { key: 'name', label: 'Name' },
  { key: 'price', label: 'Price' },
  { key: 'change', label: 'Chg%' },
  { key: 'volume', label: 'Volume' },
  { key: 'marketCap', label: 'MCap' },
  { key: 'pe', label: 'P/E' },
  { key: 'pb', label: 'P/B' },
  { key: 'divYield', label: 'DivYld' },
  { key: 'sector', label: 'Sector' },
] as const;

type SortDir = 'asc' | 'desc';

export default function StudioPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>('Workbench');

  // Selected symbol for workbench
  const selectedSymbol = 'BBCA.JK'; // TODO: make dynamic when sidebar instrument selection is wired

  // Workbench state
  const [search, setSearch] = useState('');
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(
    Object.fromEntries(METRIC_SECTIONS.map((s) => [s.label, true])),
  );
  const [timeRange, setTimeRange] = useState('1M');
  const [indicators, setIndicators] = useState(['SMA 20', 'RSI 14', 'Volume']);

  // Screener state
  const [sortCol, setSortCol] = useState<string>('symbol');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [sectorFilter, setSectorFilter] = useState('All');

  // Real data hooks
  const { data: quote } = useQuote(selectedSymbol);
  const { data: rawOhlcv, isLoading: chartLoading } = useOHLCV(selectedSymbol, '3mo');

  // Convert API OHLCV (date string) to CandlestickChart format (epoch seconds)
  const chartData: OHLCV[] = useMemo(() => {
    const raw = rawOhlcv ?? generateOHLCV(9875, 120);
    return raw.map((d) => ({
      timestamp: Math.floor(new Date(d.date).getTime() / 1000),
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
      volume: d.volume,
    }));
  }, [rawOhlcv]);

  // Chart header: use real quote with fallback
  const displayPrice = quote?.price ?? 9875;
  const displayChange = quote?.change ?? 0;
  const displayChangePct = quote?.changePct ?? 0;
  const displayName = quote?.name ?? 'Bank Central Asia';
  const displaySymbol = quote?.symbol?.replace('.JK', '') ?? selectedSymbol.replace('.JK', '');

  // Screener data
  const { data: realStocks } = useScreener();
  const screenerRaw = useMemo(() => {
    if (!realStocks) return generateScreenerData(40);
    return realStocks.map((s) => ({
      symbol: s.symbol,
      name: s.name,
      price: s.price,
      change: s.changePct,
      volume: s.volume,
      marketCap: s.marketCap,
      pe: s.peRatio ?? 0,
      pb: s.pbRatio ?? 0,
      divYield: s.divYield ?? 0,
      sector: 'N/A',
    }));
  }, [realStocks]);
  const sectors = useMemo(() => ['All', ...Array.from(new Set(screenerRaw.map((r) => r.sector)))], [screenerRaw]);

  const screenerData = useMemo(() => {
    let rows = sectorFilter === 'All' ? screenerRaw : screenerRaw.filter((r) => r.sector === sectorFilter);
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol as keyof typeof a];
      const bv = b[sortCol as keyof typeof b];
      if (typeof av === 'number' && typeof bv === 'number') return sortDir === 'asc' ? av - bv : bv - av;
      return sortDir === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    return rows;
  }, [screenerRaw, sectorFilter, sortCol, sortDir]);

  const toggleSection = (label: string) =>
    setOpenSections((p) => ({ ...p, [label]: !p[label] }));

  const handleSort = (key: string) => {
    if (sortCol === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortCol(key); setSortDir('asc'); }
  };

  const fmtNum = (n: number) => n >= 1e12 ? `${(n / 1e12).toFixed(1)}T` : n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n.toLocaleString();

  return (
    <div className="flex min-h-full flex-col p-4">
      {/* Header + Tabs */}
      <div className="mb-2 flex items-center gap-6 border-b border-[#1e1e22]">
        <span className="pb-2 text-sm font-medium text-white/70">Studio</span>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-xs transition-colors ${
              tab === t
                ? 'border-b-2 border-[var(--accent-500)] text-white'
                : 'text-white/40 hover:text-white/60'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── WORKBENCH ── */}
      {tab === 'Workbench' && (
        <div className="flex flex-1 gap-2 overflow-hidden" style={{ minHeight: 0 }}>
          {/* Sidebar */}
          <div className="w-[200px] shrink-0 overflow-y-auto rounded border border-[#1e1e22] bg-[#0a0a0c]">
            <input
              type="text"
              placeholder="Search metrics..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full border-b border-[#1e1e22] bg-[#0a0a0c] px-2 py-1.5 text-xs text-white/70 outline-none placeholder:text-white/20"
            />
            {METRIC_SECTIONS.map((sec) => {
              const filtered = sec.items.filter((it) => it.toLowerCase().includes(search.toLowerCase()));
              if (search && filtered.length === 0) return null;
              const open = openSections[sec.label];
              return (
                <div key={sec.label}>
                  <button
                    onClick={() => toggleSection(sec.label)}
                    className="flex w-full items-center gap-1 px-2 py-1.5 text-[10px] font-medium uppercase tracking-wider text-white/30 hover:text-white/50"
                  >
                    <span className="w-3 text-[8px]">{open ? '▾' : '▸'}</span>
                    {sec.label}
                  </button>
                  {open && filtered.map((item) => (
                    <div key={item} className="cursor-pointer px-2 py-1.5 text-xs text-white/50 hover:bg-white/[0.03]">
                      {item}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>

          {/* Chart area */}
          <div className="flex flex-1 flex-col gap-2 overflow-hidden">
            <div className="flex items-baseline gap-2 font-mono text-sm text-white/80">
              <span className="font-medium text-white">{displaySymbol}</span>
              <span className="text-white/40">{displayName}</span>
              <span>{displayPrice.toLocaleString()}</span>
              <span className={displayChange >= 0 ? 'text-green-500' : 'text-red-500'}>
                {displayChange >= 0 ? '+' : ''}{displayChange.toFixed(0)} ({displayChange >= 0 ? '+' : ''}{displayChangePct.toFixed(2)}%)
              </span>
            </div>
            <div className="flex-1" style={{ minHeight: 350 }}>
              {chartLoading ? (
                <CandlestickChartSkeleton height={350} />
              ) : (
                <CandlestickChart data={chartData} height={350} />
              )}
            </div>
            <div className="flex items-center gap-2">
              {TIME_RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setTimeRange(r)}
                  className={`rounded px-2 py-0.5 text-[10px] font-medium ${
                    timeRange === r ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/50'
                  }`}
                >
                  {r}
                </button>
              ))}
              <div className="ml-auto flex items-center gap-1">
                {indicators.map((ind) => (
                  <span key={ind} className="flex items-center gap-1 rounded bg-white/[0.06] px-2 py-0.5 text-[10px] text-white/50">
                    {ind}
                    <button onClick={() => setIndicators((p) => p.filter((x) => x !== ind))} className="ml-0.5 text-white/30 hover:text-white/60">&times;</button>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── DASHBOARDS ── */}
      {tab === 'Dashboards' && (
        <div className="flex flex-1 flex-col items-center justify-center gap-4">
          <p className="text-sm text-white/30">Create your first dashboard</p>
          <button className="rounded border border-[var(--accent-500)] px-3 py-1.5 text-xs text-[var(--accent-500)] hover:bg-[var(--accent-500)]/10">
            + New Dashboard
          </button>
          <div className="mt-4 grid w-full max-w-md grid-cols-2 gap-2">
            {['IDX Sector Overview', 'LQ45 Heatmap'].map((name) => (
              <div key={name} className="rounded border border-[#1e1e22] bg-[#0a0a0c] p-3">
                <p className="text-xs font-medium text-white/60">{name}</p>
                <p className="mt-1 text-[10px] text-white/20">4 tiles</p>
                <p className="text-[10px] text-white/20">Last modified 2d ago</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── SCREENER ── */}
      {tab === 'Screener' && (
        <div className="flex flex-1 flex-col gap-2 overflow-hidden">
          <div className="flex items-center gap-2">
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="rounded border border-[#1e1e22] bg-[#0a0a0c] px-2 py-1 text-xs text-white/60 outline-none"
            >
              {sectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <span className="text-[10px] text-white/20">{screenerData.length} results</span>
          </div>
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#1e1e22]">
                  {SCREENER_COLS.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className="cursor-pointer whitespace-nowrap px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-white/30 hover:text-white/50"
                    >
                      {col.label}
                      {sortCol === col.key && <span className="ml-0.5">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {screenerData.map((row) => (
                  <tr
                    key={row.symbol}
                    onClick={() => router.push(`/markets/${row.symbol}`)}
                    className="cursor-pointer border-b border-[#1e1e22] transition-colors hover:bg-white/[0.02]"
                  >
                    <td className="px-3 py-2 font-mono text-xs font-medium text-white/70">{row.symbol}</td>
                    <td className="px-3 py-2 text-xs text-white/40">{row.name}</td>
                    <td className="px-3 py-2 font-mono text-xs text-white/60">{row.price.toLocaleString()}</td>
                    <td className={`px-3 py-2 font-mono text-xs ${row.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {row.change >= 0 ? '+' : ''}{row.change.toFixed(2)}%
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-white/40">{fmtNum(row.volume)}</td>
                    <td className="px-3 py-2 font-mono text-xs text-white/40">{fmtNum(row.marketCap)}</td>
                    <td className="px-3 py-2 font-mono text-xs text-white/40">{row.pe.toFixed(1)}</td>
                    <td className="px-3 py-2 font-mono text-xs text-white/40">{row.pb.toFixed(1)}</td>
                    <td className="px-3 py-2 font-mono text-xs text-white/40">{row.divYield.toFixed(1)}%</td>
                    <td className="px-3 py-2 text-xs text-white/30">{row.sector}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <TerminalDisclaimer />
    </div>
  );
}
