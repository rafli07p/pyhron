import { useState } from 'react';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import DataTable, { type Column } from '@/shared_ui_components/DataTable';
import { useNavigate } from 'react-router-dom';

interface ScreenerResult {
  ticker: string;
  name: string;
  sector: string;
  pe_ratio: number;
  pb_ratio: number;
  roe: number;
  dividend_yield: number;
  market_cap: number;
  [key: string]: unknown;
}

const mockResults: ScreenerResult[] = [
  { ticker: 'BBCA', name: 'Bank Central Asia', sector: 'Financials', pe_ratio: 24.5, pb_ratio: 4.2, roe: 18.3, dividend_yield: 1.8, market_cap: 1210e12 },
  { ticker: 'TLKM', name: 'Telkom Indonesia', sector: 'Telecom', pe_ratio: 16.2, pb_ratio: 3.1, roe: 21.5, dividend_yield: 4.2, market_cap: 392e12 },
  { ticker: 'UNVR', name: 'Unilever Indonesia', sector: 'Consumer', pe_ratio: 32.1, pb_ratio: 28.5, roe: 95.2, dividend_yield: 2.9, market_cap: 152e12 },
  { ticker: 'ICBP', name: 'Indofood CBP', sector: 'Consumer', pe_ratio: 18.7, pb_ratio: 3.8, roe: 19.1, dividend_yield: 2.1, market_cap: 109e12 },
];

const columns: Column<ScreenerResult>[] = [
  { key: 'ticker', label: 'Ticker', align: 'left', sortable: true, render: (r) => <span className="text-bloomberg-accent font-bold">{r.ticker}</span> },
  { key: 'name', label: 'Name', align: 'left', sortable: true },
  { key: 'sector', label: 'Sector', align: 'left', sortable: true },
  { key: 'pe_ratio', label: 'P/E', align: 'right', sortable: true, render: (r) => r.pe_ratio.toFixed(1) },
  { key: 'pb_ratio', label: 'P/B', align: 'right', sortable: true, render: (r) => r.pb_ratio.toFixed(1) },
  { key: 'roe', label: 'ROE %', align: 'right', sortable: true, render: (r) => r.roe.toFixed(1) },
  { key: 'dividend_yield', label: 'Div %', align: 'right', sortable: true, render: (r) => r.dividend_yield.toFixed(1) },
];

export default function ScreenerPage() {
  const navigate = useNavigate();
  const [minPE, setMinPE] = useState('');
  const [maxPE, setMaxPE] = useState('');
  const [sector, setSector] = useState('All');

  const filtered = mockResults.filter((r) => {
    if (sector !== 'All' && r.sector !== sector) return false;
    if (minPE && r.pe_ratio < Number(minPE)) return false;
    if (maxPE && r.pe_ratio > Number(maxPE)) return false;
    return true;
  });

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">Stock Screener</h2>

      <DashboardCard title="Filters" dense>
        <div className="flex items-center gap-4 flex-wrap">
          <label className="flex items-center gap-1 text-xs text-bloomberg-text-secondary">
            Sector
            <select value={sector} onChange={(e) => setSector(e.target.value)} className="bg-bloomberg-bg-tertiary text-bloomberg-text-primary border border-bloomberg-border rounded px-2 py-1 text-xs font-mono">
              <option>All</option>
              <option>Financials</option>
              <option>Telecom</option>
              <option>Consumer</option>
              <option>Energy</option>
              <option>Materials</option>
            </select>
          </label>
          <label className="flex items-center gap-1 text-xs text-bloomberg-text-secondary">
            P/E Min
            <input type="number" value={minPE} onChange={(e) => setMinPE(e.target.value)} className="bg-bloomberg-bg-tertiary text-bloomberg-text-primary border border-bloomberg-border rounded px-2 py-1 text-xs font-mono w-16" />
          </label>
          <label className="flex items-center gap-1 text-xs text-bloomberg-text-secondary">
            P/E Max
            <input type="number" value={maxPE} onChange={(e) => setMaxPE(e.target.value)} className="bg-bloomberg-bg-tertiary text-bloomberg-text-primary border border-bloomberg-border rounded px-2 py-1 text-xs font-mono w-16" />
          </label>
        </div>
      </DashboardCard>

      <DashboardCard title="Results" subtitle={`${filtered.length} stocks`}>
        <DataTable columns={columns} data={filtered} rowKey={(r) => r.ticker} onRowClick={(r) => navigate(`/stock/${r.ticker}`)} />
      </DashboardCard>
    </div>
  );
}
