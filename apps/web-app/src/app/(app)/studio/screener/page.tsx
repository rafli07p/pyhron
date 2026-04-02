'use client';

import { useState } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { Badge } from '@/design-system/primitives/Badge';
import { useTierGate } from '@/hooks/useTierGate';
import { Search, Filter, Download } from 'lucide-react';

const sectors = ['All Sectors', 'Financials', 'Consumer Staples', 'Telecom', 'Industrials', 'Mining', 'Energy', 'Property'];

const sampleStocks = [
  { symbol: 'BBCA', name: 'Bank Central Asia', sector: 'Financials', price: 9875, change: 1.28, volume: 12_450_000, mcap: '1,215T', pe: 24.3, pb: 4.8, roe: 20.1 },
  { symbol: 'BMRI', name: 'Bank Mandiri', sector: 'Financials', price: 6225, change: 0.81, volume: 18_320_000, mcap: '580T', pe: 11.2, pb: 2.1, roe: 19.4 },
  { symbol: 'TLKM', name: 'Telkom Indonesia', sector: 'Telecom', price: 3850, change: -1.12, volume: 24_100_000, mcap: '381T', pe: 16.8, pb: 3.2, roe: 18.7 },
  { symbol: 'ASII', name: 'Astra International', sector: 'Industrials', price: 5425, change: -0.46, volume: 9_870_000, mcap: '219T', pe: 8.4, pb: 1.4, roe: 16.2 },
  { symbol: 'UNVR', name: 'Unilever Indonesia', sector: 'Consumer Staples', price: 4120, change: 0.24, volume: 5_430_000, mcap: '157T', pe: 32.1, pb: 28.4, roe: 88.5 },
  { symbol: 'BBNI', name: 'Bank Negara Indonesia', sector: 'Financials', price: 5075, change: 1.60, volume: 15_670_000, mcap: '189T', pe: 8.9, pb: 1.3, roe: 14.8 },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia', sector: 'Financials', price: 4890, change: 2.30, volume: 32_100_000, mcap: '736T', pe: 12.4, pb: 2.6, roe: 21.3 },
  { symbol: 'MDKA', name: 'Merdeka Copper Gold', sector: 'Mining', price: 2710, change: -2.51, volume: 8_920_000, mcap: '58T', pe: 45.2, pb: 3.1, roe: 6.8 },
];

const columns = ['Symbol', 'Name', 'Sector', 'Price', 'Change %', 'Volume', 'MCap', 'P/E', 'P/B', 'ROE'];

export default function ScreenerPage() {
  const { hasAccess } = useTierGate('markets.screener.full');
  const [selectedSector, setSelectedSector] = useState('All Sectors');
  const [lq45Only, setLq45Only] = useState(false);

  const filteredStocks = sampleStocks.filter((s) => {
    if (selectedSector !== 'All Sectors' && s.sector !== selectedSector) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stock Screener"
        description="Filter and rank IDX stocks by fundamental and technical criteria"
        actions={
          <Button variant="outline" size="sm">
            <Download className="h-3.5 w-3.5" />
            Export
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
        {/* Filters Sidebar */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-3.5 w-3.5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Sector</label>
                <select
                  value={selectedSector}
                  onChange={(e) => setSelectedSector(e.target.value)}
                  className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]"
                >
                  {sectors.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Market Cap (T IDR)</label>
                <div className="flex gap-2">
                  <input type="number" placeholder="Min" className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]" />
                  <input type="number" placeholder="Max" className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]" />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">P/E Ratio</label>
                <div className="flex gap-2">
                  <input type="number" placeholder="Min" className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]" />
                  <input type="number" placeholder="Max" className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]" />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">ROE Min (%)</label>
                <input type="number" placeholder="e.g. 15" className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]" />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Dividend Yield Min (%)</label>
                <input type="number" placeholder="e.g. 2" className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]" />
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setLq45Only(!lq45Only)}
                  className={`relative h-5 w-9 rounded-full transition-colors ${lq45Only ? 'bg-[var(--accent-500)]' : 'bg-[var(--surface-3)]'}`}
                >
                  <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${lq45Only ? 'left-[18px]' : 'left-0.5'}`} />
                </button>
                <span className="text-xs text-[var(--text-secondary)]">LQ45 Only</span>
              </div>

              <Button variant="primary" size="sm" className="w-full">
                <Search className="h-3.5 w-3.5" />
                Apply Filters
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Results Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{filteredStocks.length} Results</CardTitle>
              {!hasAccess && (
                <Badge variant="warning">Limited - Upgrade for full access</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    {columns.map((col) => (
                      <th
                        key={col}
                        className="px-3 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredStocks.map((stock) => (
                    <tr
                      key={stock.symbol}
                      className="border-b border-[var(--border-default)] transition-colors last:border-0 hover:bg-[var(--surface-2)]"
                    >
                      <td className="px-3 py-2 text-sm font-medium text-[var(--accent-500)]">{stock.symbol}</td>
                      <td className="px-3 py-2 text-sm text-[var(--text-primary)]">{stock.name}</td>
                      <td className="px-3 py-2 text-xs text-[var(--text-secondary)]">{stock.sector}</td>
                      <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-primary)]">{stock.price.toLocaleString('id-ID')}</td>
                      <td className={`px-3 py-2 tabular-nums text-sm font-medium ${stock.change >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                        {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                      </td>
                      <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{stock.volume.toLocaleString('id-ID')}</td>
                      <td className="px-3 py-2 text-sm text-[var(--text-secondary)]">{stock.mcap}</td>
                      <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{stock.pe.toFixed(1)}</td>
                      <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{stock.pb.toFixed(1)}</td>
                      <td className="px-3 py-2 tabular-nums text-sm text-[var(--text-secondary)]">{stock.roe.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
