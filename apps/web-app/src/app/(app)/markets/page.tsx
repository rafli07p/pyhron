'use client';

import { useState, useEffect, useMemo, useCallback, useTransition } from 'react';
import Link from 'next/link';
import { MiniChart } from '@/design-system/charts/MiniChart';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';
import { INDICES, SECTORS, MARKET_BREADTH, generateSparkline } from '@/mocks/terminal-data';
import { fetchAllStocks, fetchRealIndices, type RealStock } from './actions';

function fmtN(n: number) {
  return n.toLocaleString('id-ID');
}
function fmtD(n: number) {
  return n.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtVol(v: number) {
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return String(v);
}
function fmtCap(v: number) {
  if (v >= 1e15) return `${(v / 1e15).toFixed(0)}T`;
  if (v >= 1e12) return `${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9) return `${(v / 1e9).toFixed(0)}B`;
  return fmtN(v);
}

type SortKey = 'symbol' | 'price' | 'changePct' | 'volume' | 'marketCap' | 'pe' | 'pb' | 'divYield';

export default function MarketsPage() {
  const [realStocks, setRealStocks] = useState<RealStock[]>([]);
  const [realIdx, setRealIdx] = useState<{ symbol: string; name: string; value: number; change: number; changePct: number }[]>([]);
  const [tab, setTab] = useState<'gainers' | 'losers' | 'active'>('gainers');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('marketCap');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [isPending, startTransition] = useTransition();
  const loading = isPending && realStocks.length === 0;

  const loadData = useCallback(() => {
    startTransition(async () => {
      try {
        const [stocks, idxData] = await Promise.all([fetchAllStocks(), fetchRealIndices()]);
        setRealStocks(stocks);
        if (idxData.length > 0) setRealIdx(idxData);
      } catch { /* fallback to mock */ }
    });
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  // Auto-refresh every 60s
  useEffect(() => { const t = setInterval(loadData, 60_000); return () => clearInterval(t); }, [loadData]);

  const indices = realIdx.length > 0 ? realIdx : INDICES;
  const hasReal = realStocks.length > 0;

  // Gainers / Losers / Most Active
  const gainers = hasReal ? [...realStocks].sort((a, b) => b.changePct - a.changePct).slice(0, 8) : [];
  const losers = hasReal ? [...realStocks].sort((a, b) => a.changePct - b.changePct).slice(0, 8) : [];
  const active = hasReal ? [...realStocks].sort((a, b) => b.volume - a.volume).slice(0, 8) : [];
  const movers = tab === 'gainers' ? gainers : tab === 'losers' ? losers : active;

  // Breadth from real data
  const breadth = useMemo(() => {
    if (!hasReal) return MARKET_BREADTH;
    return {
      advancing: realStocks.filter((s) => s.changePct > 0).length,
      declining: realStocks.filter((s) => s.changePct < 0).length,
      unchanged: realStocks.filter((s) => s.changePct === 0).length,
    };
  }, [realStocks, hasReal]);
  const total = breadth.advancing + breadth.declining + breadth.unchanged;

  // Sectors from real data
  const sectors = useMemo(() => {
    if (!hasReal) return SECTORS;
    const map = new Map<string, { total: number; count: number }>();
    for (const s of realStocks) {
      const e = map.get(s.sector) ?? { total: 0, count: 0 };
      e.total += s.changePct;
      e.count += 1;
      map.set(s.sector, e);
    }
    return Array.from(map, ([name, d]) => ({
      name,
      change: Math.round((d.total / d.count) * 100) / 100,
      weight: Math.round((d.count / realStocks.length) * 100),
    }));
  }, [realStocks, hasReal]);

  // Sortable + searchable stock table
  const filtered = useMemo(() => {
    let list = hasReal ? realStocks : [];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q));
    }
    return [...list].sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return sortDir === 'desc' ? (bv as number) - (av as number) : (av as number) - (bv as number);
    });
  }, [realStocks, hasReal, search, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('desc'); }
  }
  const arrow = (k: SortKey) => sortKey === k ? (sortDir === 'asc' ? ' ↑' : ' ↓') : '';

  function exportCSV() {
    const hdr = ['Symbol', 'Name', 'Price', 'Change%', 'Volume', 'MCap', 'P/E', 'P/B', 'DivYield%', 'Sector'];
    const rows = filtered.map((s) => [s.symbol, s.name, s.price, s.changePct.toFixed(2), s.volume, s.marketCap, s.pe ?? '', s.pb ?? '', s.divYield ?? '', s.sector]);
    const csv = [hdr, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pyhron-markets-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-3 p-4">
      <h1 className="terminal-page-title">Markets</h1>

      {/* Index cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {indices.map((idx) => {
          const pos = idx.changePct >= 0;
          const spark = generateSparkline(20, idx.value, 50);
          return (
            <div key={idx.symbol} className="rounded-lg border border-[#1e1e22] bg-[#111113] p-3">
              <div className="stat-label">{idx.symbol}</div>
              {loading && !realIdx.length ? (
                <div className="mt-1 h-5 w-20 animate-pulse rounded bg-white/[0.03]" />
              ) : (
                <div className="stat-value text-lg">{fmtD(idx.value)}</div>
              )}
              <div className="flex items-center justify-between">
                <span className={`font-mono text-xs ${pos ? 'pnl-positive' : 'pnl-negative'}`}>
                  {pos ? '+' : ''}{idx.changePct.toFixed(2)}%
                </span>
                <MiniChart data={spark} width={60} height={20} positive={pos} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Market Breadth */}
      <div className="rounded-lg border border-[#1e1e22] bg-[#111113] p-3">
        <div className="mb-2 flex items-center justify-between text-xs text-white/50">
          <span>Market Breadth</span>
          <span className="font-mono">
            <span className="pnl-positive">Adv {breadth.advancing}</span>
            {' | '}
            <span className="pnl-negative">Dec {breadth.declining}</span>
            {' | '}
            <span className="text-white/40">Unch {breadth.unchanged}</span>
          </span>
        </div>
        <div className="flex h-2 w-full overflow-hidden rounded-full">
          <div className="bg-emerald-500" style={{ width: `${total ? (breadth.advancing / total) * 100 : 0}%` }} />
          <div className="bg-red-500" style={{ width: `${total ? (breadth.declining / total) * 100 : 0}%` }} />
          <div className="bg-white/20" style={{ width: `${total ? (breadth.unchanged / total) * 100 : 0}%` }} />
        </div>
      </div>

      {/* Sector Heatmap */}
      <div>
        <div className="terminal-heading mb-2">Sector Heatmap</div>
        <div className="grid grid-cols-3 gap-1">
          {sectors.map((s) => {
            const pos = s.change >= 0;
            const mag = Math.min(Math.abs(s.change) / 3, 1);
            const bg = pos ? `rgba(34,197,94,${0.08 + mag * 0.22})` : `rgba(239,68,68,${0.08 + mag * 0.22})`;
            return (
              <div key={s.name} className="flex flex-col items-center justify-center rounded-md p-2" style={{ minHeight: 50, backgroundColor: bg }}>
                <span className="text-xs text-white/70">{s.name}</span>
                <span className={`font-mono text-sm ${pos ? 'pnl-positive' : 'pnl-negative'}`}>
                  {pos ? '+' : ''}{s.change.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Movers (Gainers / Losers / Most Active) */}
      <div>
        <div className="mb-2 flex items-center gap-1">
          {(['gainers', 'losers', 'active'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                tab === t
                  ? t === 'losers' ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                  : 'text-white/40 hover:text-white/60'
              }`}
            >
              {t === 'gainers' ? 'Gainers' : t === 'losers' ? 'Losers' : 'Most Active'}
            </button>
          ))}
        </div>
        <div className="overflow-hidden rounded-lg border border-[#1e1e22] bg-[#111113]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e1e22]">
                <th className="table-header px-3 py-2 text-left">Symbol</th>
                <th className="table-header px-3 py-2 text-left">Name</th>
                <th className="table-header px-3 py-2 text-right">Price</th>
                <th className="table-header px-3 py-2 text-right">Change%</th>
                <th className="table-header px-3 py-2 text-right">Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e22]">
              {movers.map((s) => {
                const pos = s.changePct >= 0;
                return (
                  <tr key={s.symbol} className="hover:bg-white/[0.02]">
                    <td className="px-3 py-2">
                      <Link href={`/markets/${s.symbol}`} className="font-mono text-sm text-white hover:underline">{s.symbol}</Link>
                    </td>
                    <td className="px-3 py-2 text-xs text-white/50">{s.name}</td>
                    <td className="px-3 py-2 text-right font-mono text-white">{fmtN(s.price)}</td>
                    <td className={`px-3 py-2 text-right font-mono font-medium ${pos ? 'pnl-positive' : 'pnl-negative'}`}>
                      {pos ? '+' : ''}{s.changePct.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-white/40">{fmtVol(s.volume)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Full Stock Table */}
      {hasReal && (
        <div>
          <div className="mb-2 flex items-center gap-3">
            <div className="terminal-heading">All Stocks</div>
            <input
              type="text"
              placeholder="Search symbol..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-7 w-48 rounded border border-[#1e1e22] bg-[#0a0a0c] px-2 text-[11px] text-white placeholder-white/20 focus:border-[#2563eb] focus:outline-none"
            />
            <button onClick={exportCSV} className="h-7 rounded border border-[#1e1e22] px-3 text-[10px] text-white/30 transition-colors hover:text-white/60">
              Export CSV
            </button>
            <button onClick={loadData} disabled={loading} className="h-7 rounded border border-[#1e1e22] px-2 text-[10px] text-white/30 transition-colors hover:text-white/60 disabled:opacity-30">
              {loading ? '...' : '↻'}
            </button>
            <span className="ml-auto font-mono text-[9px] text-white/15">{filtered.length} stocks · Yahoo Finance</span>
          </div>
          <div className="overflow-hidden rounded-lg border border-[#1e1e22] bg-[#111113]">
            <div className="max-h-[400px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-[#111113]">
                  <tr className="border-b border-[#1e1e22]">
                    <th onClick={() => toggleSort('symbol')} className="table-header cursor-pointer px-3 py-2 text-left hover:text-white/50">SYM{arrow('symbol')}</th>
                    <th className="table-header px-3 py-2 text-left">NAME</th>
                    <th onClick={() => toggleSort('price')} className="table-header cursor-pointer px-3 py-2 text-right hover:text-white/50">PRICE{arrow('price')}</th>
                    <th onClick={() => toggleSort('changePct')} className="table-header cursor-pointer px-3 py-2 text-right hover:text-white/50">CHG%{arrow('changePct')}</th>
                    <th onClick={() => toggleSort('volume')} className="table-header cursor-pointer px-3 py-2 text-right hover:text-white/50">VOL{arrow('volume')}</th>
                    <th onClick={() => toggleSort('marketCap')} className="table-header cursor-pointer px-3 py-2 text-right hover:text-white/50">MCAP{arrow('marketCap')}</th>
                    <th onClick={() => toggleSort('pe')} className="table-header cursor-pointer px-3 py-2 text-right hover:text-white/50">P/E{arrow('pe')}</th>
                    <th onClick={() => toggleSort('pb')} className="table-header hidden cursor-pointer px-3 py-2 text-right hover:text-white/50 lg:table-cell">P/B{arrow('pb')}</th>
                    <th onClick={() => toggleSort('divYield')} className="table-header hidden cursor-pointer px-3 py-2 text-right hover:text-white/50 lg:table-cell">DIV%{arrow('divYield')}</th>
                    <th className="table-header hidden px-3 py-2 text-center lg:table-cell">52W</th>
                    <th className="table-header hidden px-3 py-2 text-left md:table-cell">SECTOR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e1e22]">
                  {filtered.map((s) => {
                    const pos = s.changePct >= 0;
                    const range = s.high52w - s.low52w;
                    const pos52 = range > 0 ? ((s.price - s.low52w) / range) * 100 : 50;
                    return (
                      <tr key={s.symbol} className="hover:bg-white/[0.02]">
                        <td className="px-3 py-2">
                          <Link href={`/markets/${s.symbol}`} className="font-mono text-xs font-medium text-white hover:underline">{s.symbol}</Link>
                        </td>
                        <td className="max-w-[120px] truncate px-3 py-2 text-xs text-white/40">{s.name}</td>
                        <td className="px-3 py-2 text-right font-mono text-xs text-white">{fmtN(s.price)}</td>
                        <td className={`px-3 py-2 text-right font-mono text-xs font-medium ${pos ? 'pnl-positive' : 'pnl-negative'}`}>
                          {pos ? '+' : ''}{s.changePct.toFixed(2)}%
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-xs text-white/40">{fmtVol(s.volume)}</td>
                        <td className="px-3 py-2 text-right font-mono text-xs text-white/50">{fmtCap(s.marketCap)}</td>
                        <td className={`px-3 py-2 text-right font-mono text-xs ${s.pe !== null && s.pe < 0 ? 'text-white/20' : 'text-white/50'}`}>
                          {s.pe !== null && isFinite(s.pe) ? s.pe.toFixed(1) : '—'}
                        </td>
                        <td className="hidden px-3 py-2 text-right font-mono text-xs text-white/50 lg:table-cell">
                          {s.pb !== null && isFinite(s.pb) ? s.pb.toFixed(1) : '—'}
                        </td>
                        <td className="hidden px-3 py-2 text-right font-mono text-xs text-white/50 lg:table-cell">
                          {s.divYield !== null && isFinite(s.divYield) ? `${s.divYield.toFixed(1)}%` : '—'}
                        </td>
                        <td className="hidden px-3 py-2 lg:table-cell">
                          <div className="flex w-20 items-center gap-1">
                            <span className="font-mono text-[7px] text-white/15">{fmtN(s.low52w)}</span>
                            <div className="relative h-1 flex-1 rounded-full bg-white/5">
                              <div className="absolute top-0 h-1 w-1.5 rounded-full bg-[#2563eb]" style={{ left: `${Math.max(0, Math.min(100, pos52))}%` }} />
                            </div>
                            <span className="font-mono text-[7px] text-white/15">{fmtN(s.high52w)}</span>
                          </div>
                        </td>
                        <td className="hidden px-3 py-2 text-xs text-white/30 md:table-cell">{s.sector}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <TerminalDisclaimer />
    </div>
  );
}
