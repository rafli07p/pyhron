'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { Badge } from '@/design-system/primitives/Badge';
import { Input } from '@/design-system/primitives/Input';
import { Skeleton } from '@/design-system/primitives/Skeleton';
import { PercentChange } from '@/design-system/data-display/PercentChange';
import { formatIDR, formatVolume } from '@/lib/format';
import { IDX } from '@/constants/idx';
import { Search, Filter, ChevronUp, ChevronDown } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* Top market-cap symbols treated as LQ45 constituents */
const LQ45_SYMBOLS = new Set([
  'BBCA','BBRI','BMRI','BREN','TLKM','ASII','BBNI','ARTO','UNVR','ADRO',
  'GOTO','HMSP','CPIN','KLBF','INDF',
]);

interface Stock {
  symbol: string; name: string; sector: string;
  last_price: number; change_pct: number; volume: number;
  market_cap_trillion: number; pe_ratio: number; pb_ratio: number;
  roe_pct: number; dividend_yield_pct: number;
}

type SortKey = keyof Pick<Stock,
  'symbol'|'name'|'sector'|'last_price'|'change_pct'|'volume'|
  'market_cap_trillion'|'pe_ratio'|'pb_ratio'|'roe_pct'|'dividend_yield_pct'>;
type SortDir = 'asc' | 'desc';

const COLUMNS: { label: string; key: SortKey; hideOnMobile?: boolean }[] = [
  { label: 'Symbol', key: 'symbol' },
  { label: 'Name', key: 'name' },
  { label: 'Sector', key: 'sector' },
  { label: 'Price', key: 'last_price' },
  { label: 'Change %', key: 'change_pct' },
  { label: 'Volume', key: 'volume' },
  { label: 'Market Cap', key: 'market_cap_trillion' },
  { label: 'P/E', key: 'pe_ratio' },
  { label: 'P/B', key: 'pb_ratio', hideOnMobile: true },
  { label: 'ROE %', key: 'roe_pct', hideOnMobile: true },
  { label: 'Div Yield %', key: 'dividend_yield_pct', hideOnMobile: true },
];

const inputCls =
  'w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-500)]';

export default function ScreenerPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Filters
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [mcapMin, setMcapMin] = useState('');
  const [mcapMax, setMcapMax] = useState('');
  const [peMin, setPeMin] = useState('');
  const [peMax, setPeMax] = useState('');
  const [roeMin, setRoeMin] = useState('');
  const [divYieldMin, setDivYieldMin] = useState('');
  const [lq45Only, setLq45Only] = useState(false);

  // Sort
  const [sortKey, setSortKey] = useState<SortKey>('market_cap_trillion');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  useEffect(() => {
    fetch(`${API_BASE}/v1/screener/screen`)
      .then((r) => r.json())
      .then((d) => setStocks(d.results))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let list = stocks;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q));
    }
    if (sector) list = list.filter((s) => s.sector === sector);
    if (mcapMin) list = list.filter((s) => s.market_cap_trillion >= Number(mcapMin));
    if (mcapMax) list = list.filter((s) => s.market_cap_trillion <= Number(mcapMax));
    if (peMin) list = list.filter((s) => s.pe_ratio >= Number(peMin));
    if (peMax) list = list.filter((s) => s.pe_ratio <= Number(peMax));
    if (roeMin) list = list.filter((s) => s.roe_pct >= Number(roeMin));
    if (divYieldMin) list = list.filter((s) => s.dividend_yield_pct >= Number(divYieldMin));
    if (lq45Only) list = list.filter((s) => LQ45_SYMBOLS.has(s.symbol));
    return list;
  }, [stocks, search, sector, mcapMin, mcapMax, peMin, peMax, roeMin, divYieldMin, lq45Only]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      const cmp = typeof av === 'string' ? (av as string).localeCompare(bv as string) : (av as number) - (bv as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('desc'); }
  }

  function resetFilters() {
    setSearch(''); setSector(''); setMcapMin(''); setMcapMax('');
    setPeMin(''); setPeMax(''); setRoeMin(''); setDivYieldMin(''); setLq45Only(false);
  }

  const filterPanel = (
    <div className="space-y-4">
      <Input label="Search" placeholder="Symbol or name..." value={search} onChange={(e) => setSearch(e.target.value)} />
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Sector</label>
        <select value={sector} onChange={(e) => setSector(e.target.value)} className={inputCls}>
          <option value="">All Sectors</option>
          {IDX.SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Market Cap (T IDR)</label>
        <div className="flex gap-2">
          <input type="number" placeholder="Min" value={mcapMin} onChange={(e) => setMcapMin(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Max" value={mcapMax} onChange={(e) => setMcapMax(e.target.value)} className={inputCls} />
        </div>
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">P/E Range</label>
        <div className="flex gap-2">
          <input type="number" placeholder="Min" value={peMin} onChange={(e) => setPeMin(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Max" value={peMax} onChange={(e) => setPeMax(e.target.value)} className={inputCls} />
        </div>
      </div>
      <Input label="ROE Min (%)" type="number" placeholder="e.g. 15" value={roeMin} onChange={(e) => setRoeMin(e.target.value)} />
      <Input label="Div Yield Min (%)" type="number" placeholder="e.g. 2" value={divYieldMin} onChange={(e) => setDivYieldMin(e.target.value)} />
      <div className="flex items-center gap-2">
        <button
          onClick={() => setLq45Only(!lq45Only)}
          className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${lq45Only ? 'bg-[var(--accent-500)]' : 'bg-[var(--surface-3)]'}`}
        >
          <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${lq45Only ? 'left-[18px]' : 'left-0.5'}`} />
        </button>
        <span className="text-xs text-[var(--text-secondary)]">LQ45 Only</span>
      </div>
      <p className="text-xs text-[var(--text-tertiary)]">
        Showing {filtered.length} of {stocks.length} instruments
      </p>
      <Button variant="ghost" size="sm" className="w-full" onClick={resetFilters}>Reset Filters</Button>
    </div>
  );

  const SortIcon = ({ col }: { col: SortKey }) =>
    sortKey !== col ? null : sortDir === 'asc' ? <ChevronUp className="inline h-3 w-3" /> : <ChevronDown className="inline h-3 w-3" />;

  return (
    <div className="space-y-3">
      <PageHeader title="Stock Screener" description="Filter and rank IDX stocks by fundamental and technical criteria" />

      {/* Mobile filter toggle */}
      <div className="md:hidden">
        <Button variant="outline" size="sm" onClick={() => setFiltersOpen(!filtersOpen)}>
          <Filter className="h-3.5 w-3.5" />{filtersOpen ? 'Hide Filters' : 'Filters'}
        </Button>
        {filtersOpen && (
          <Card className="mt-3">
            <CardContent className="pt-4">{filterPanel}</CardContent>
          </Card>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[260px_1fr]">
        {/* Desktop sidebar */}
        <Card className="hidden h-fit md:block">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Filter className="h-3.5 w-3.5" />Filters</CardTitle>
          </CardHeader>
          <CardContent>{filterPanel}</CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader>
            <CardTitle>
              {loading ? 'Loading...' : `${sorted.length} Result${sorted.length !== 1 ? 's' : ''}`}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="space-y-3 p-4">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full bg-[var(--surface-3)]" />
                ))}
              </div>
            ) : sorted.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-16 text-center">
                <Search className="h-8 w-8 text-[var(--text-tertiary)]" />
                <p className="text-sm text-[var(--text-secondary)]">No instruments match your filters.</p>
                <Button variant="ghost" size="sm" onClick={resetFilters}>Reset Filters</Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10 bg-[var(--surface-1)]">
                    <tr className="border-b border-[var(--border-default)]">
                      {COLUMNS.map((col) => (
                        <th
                          key={col.key}
                          onClick={() => toggleSort(col.key)}
                          className={`cursor-pointer select-none whitespace-nowrap px-3 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)] hover:text-[var(--text-primary)] ${col.hideOnMobile ? 'hidden md:table-cell' : ''}`}
                        >
                          {col.label} <SortIcon col={col.key} />
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((s, i) => (
                      <tr
                        key={s.symbol}
                        className={`border-b border-[var(--border-default)] transition-colors last:border-0 hover:bg-[var(--surface-2)] ${i % 2 === 1 ? 'bg-[var(--surface-1)]/50' : ''}`}
                      >
                        <td className="px-3 py-2 font-medium">
                          <Link href={`/markets/${s.symbol}`} className="text-[var(--accent-500)] hover:underline">{s.symbol}</Link>
                        </td>
                        <td className="max-w-[160px] truncate px-3 py-2 text-[var(--text-primary)]">{s.name}</td>
                        <td className="px-3 py-2"><Badge variant="outline" className="whitespace-nowrap">{s.sector}</Badge></td>
                        <td className="whitespace-nowrap px-3 py-2 tabular-nums text-[var(--text-primary)]">{formatIDR(s.last_price)}</td>
                        <td className="px-3 py-2"><PercentChange value={s.change_pct} size="sm" /></td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{formatVolume(s.volume)}</td>
                        <td className="whitespace-nowrap px-3 py-2 tabular-nums text-[var(--text-secondary)]">IDR {s.market_cap_trillion}T</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{s.pe_ratio.toFixed(1)}</td>
                        <td className="hidden px-3 py-2 tabular-nums text-[var(--text-secondary)] md:table-cell">{s.pb_ratio.toFixed(1)}</td>
                        <td className={`hidden px-3 py-2 tabular-nums md:table-cell ${s.roe_pct >= 15 ? 'text-[var(--positive)]' : 'text-[var(--text-secondary)]'}`}>{s.roe_pct.toFixed(1)}%</td>
                        <td className="hidden px-3 py-2 tabular-nums text-[var(--text-secondary)] md:table-cell">{s.dividend_yield_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
