'use client';

import { useState, useMemo } from 'react';
import { mockScreenerResults } from '@/lib/mock/data/instruments';
import { formatIDR, formatPct, pctColor } from '@/lib/utils/format';
import { ArrowUpDown, Download } from 'lucide-react';
import type { ScreenerResult } from '@/types/screener';

const sectors = ['All', 'Financials', 'Energy', 'Materials', 'Consumer Staples', 'Consumer Discretionary', 'Communication Services', 'Health Care', 'Utilities'];

type SortKey = keyof ScreenerResult;

export function ScreenerView() {
  const [sectorFilter, setSectorFilter] = useState('All');
  const [lq45Only, setLq45Only] = useState(false);
  const [sortBy, setSortBy] = useState<SortKey>('market_cap');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const filtered = useMemo(() => {
    let results = [...mockScreenerResults];
    if (sectorFilter !== 'All') results = results.filter((r) => r.sector === sectorFilter);
    if (lq45Only) results = results.filter((r) => r.is_lq45);
    results.sort((a, b) => {
      const av = a[sortBy] ?? 0;
      const bv = b[sortBy] ?? 0;
      const cmp = (av as number) - (bv as number);
      return sortDir === 'desc' ? -cmp : cmp;
    });
    return results;
  }, [sectorFilter, lq45Only, sortBy, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(key);
      setSortDir('desc');
    }
  };

  const handleExportCSV = () => {
    const csv = ['Symbol,Name,Sector,Price,Change%,Market Cap,P/E,P/B,ROE,Div Yield']
      .concat(filtered.map((r) => `${r.symbol},${r.name},${r.sector},${r.last_price},${r.change_pct},${r.market_cap},${r.pe_ratio},${r.pbv_ratio},${r.roe},${r.dividend_yield}`))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pyhron-screener.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns: { key: SortKey; label: string; align: 'left' | 'right'; format: (r: ScreenerResult) => React.ReactNode }[] = [
    { key: 'symbol', label: 'Ticker', align: 'left', format: (r) => <span className="font-medium font-mono">{r.symbol}</span> },
    { key: 'name', label: 'Name', align: 'left', format: (r) => <span className="text-text-secondary truncate max-w-[200px] block">{r.name}</span> },
    { key: 'last_price', label: 'Price', align: 'right', format: (r) => <span className="font-mono">{r.last_price.toLocaleString('id-ID')}</span> },
    { key: 'change_pct', label: 'Change', align: 'right', format: (r) => <span className={`font-mono ${pctColor(r.change_pct)}`}>{formatPct(r.change_pct)}</span> },
    { key: 'market_cap', label: 'Mkt Cap', align: 'right', format: (r) => <span className="font-mono">{formatIDR(r.market_cap)}</span> },
    { key: 'pe_ratio', label: 'P/E', align: 'right', format: (r) => <span className="font-mono">{r.pe_ratio?.toFixed(1) ?? '\u2014'}</span> },
    { key: 'pbv_ratio', label: 'P/B', align: 'right', format: (r) => <span className="font-mono">{r.pbv_ratio?.toFixed(1) ?? '\u2014'}</span> },
    { key: 'roe', label: 'ROE', align: 'right', format: (r) => <span className="font-mono">{r.roe ? `${r.roe.toFixed(1)}%` : '\u2014'}</span> },
    { key: 'dividend_yield', label: 'Div Yield', align: 'right', format: (r) => <span className="font-mono">{r.dividend_yield ? `${r.dividend_yield.toFixed(1)}%` : '\u2014'}</span> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <select value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)} className="rounded-md border border-border bg-bg-primary px-3 py-2 text-sm focus:border-accent-500 focus:outline-none">
          {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          <input type="checkbox" checked={lq45Only} onChange={(e) => setLq45Only(e.target.checked)} className="rounded" />
          LQ45 only
        </label>
        <button onClick={handleExportCSV} className="ml-auto flex items-center gap-1 rounded-md border border-border px-3 py-2 text-sm text-text-secondary hover:bg-bg-tertiary">
          <Download className="h-3.5 w-3.5" /> CSV
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-bg-secondary">
              {columns.map((col) => (
                <th key={col.key} className={`px-3 py-2.5 font-medium text-text-muted whitespace-nowrap cursor-pointer hover:text-text-primary ${col.align === 'right' ? 'text-right' : 'text-left'}`} onClick={() => handleSort(col.key)}>
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    <ArrowUpDown className="h-3 w-3" />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, i) => (
              <tr key={row.symbol} className={`border-b border-border last:border-0 hover:bg-bg-secondary ${i % 2 === 0 ? '' : 'bg-bg-secondary/50'}`} style={{ height: 36 }}>
                {columns.map((col) => (
                  <td key={col.key} className={`px-3 py-1.5 ${col.align === 'right' ? 'text-right' : 'text-left'}`}>
                    {col.format(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-text-muted">{filtered.length} stocks found</p>
    </div>
  );
}
