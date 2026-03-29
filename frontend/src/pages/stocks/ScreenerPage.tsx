import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Search, RotateCcw } from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import DataTable from '../../components/common/DataTable';
import type { Column } from '../../components/common/DataTable';
import { screenerApi } from '../../api/endpoints';
import type { ScreenerResult } from '../../types';

function formatNumber(value: number): string {
  if (value >= 1_000_000_000_000) return (value / 1_000_000_000_000).toFixed(2) + 'T';
  if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(2) + 'B';
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(2) + 'M';
  if (value >= 1_000) return (value / 1_000).toFixed(2) + 'K';
  return value.toFixed(2);
}

function formatPrice(value: number): string {
  return value.toLocaleString('id-ID', { maximumFractionDigits: 0 });
}

const SECTORS = [
  'Basic Materials',
  'Consumer Cyclicals',
  'Consumer Non-Cyclicals',
  'Energy',
  'Financials',
  'Healthcare',
  'Industrials',
  'Infrastructures',
  'Properties & Real Estate',
  'Technology',
  'Telecommunications',
  'Transportation & Logistics',
];

const SORT_OPTIONS = [
  { value: 'market_cap', label: 'Market Cap' },
  { value: 'change_pct', label: 'Change %' },
  { value: 'volume', label: 'Volume' },
  { value: 'pe_ratio', label: 'P/E Ratio' },
  { value: 'pbv_ratio', label: 'P/BV Ratio' },
  { value: 'roe', label: 'ROE' },
  { value: 'dividend_yield', label: 'Dividend Yield' },
];

interface Filters {
  sector: string;
  min_market_cap: string;
  max_market_cap: string;
  min_pe: string;
  max_pe: string;
  min_pbv: string;
  max_pbv: string;
  min_roe: string;
  min_dividend_yield: string;
  lq45_only: boolean;
  sort_by: string;
  sort_dir: string;
}

const defaultFilters: Filters = {
  sector: '',
  min_market_cap: '',
  max_market_cap: '',
  min_pe: '',
  max_pe: '',
  min_pbv: '',
  max_pbv: '',
  min_roe: '',
  min_dividend_yield: '',
  lq45_only: false,
  sort_by: 'market_cap',
  sort_dir: 'desc',
};

export default function ScreenerPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(defaultFilters);

  const buildParams = (f: Filters) => {
    const params: Record<string, unknown> = {
      sort_by: f.sort_by,
      sort_dir: f.sort_dir,
      limit: 50,
    };
    if (f.sector) params.sector = f.sector;
    if (f.min_market_cap) params.min_market_cap = Number(f.min_market_cap);
    if (f.max_market_cap) params.max_market_cap = Number(f.max_market_cap);
    if (f.min_pe) params.min_pe = Number(f.min_pe);
    if (f.max_pe) params.max_pe = Number(f.max_pe);
    if (f.min_pbv) params.min_pbv = Number(f.min_pbv);
    if (f.max_pbv) params.max_pbv = Number(f.max_pbv);
    if (f.min_roe) params.min_roe = Number(f.min_roe);
    if (f.min_dividend_yield) params.min_dividend_yield = Number(f.min_dividend_yield);
    if (f.lq45_only) params.lq45_only = true;
    return params;
  };

  const { data, isLoading } = useQuery({
    queryKey: ['screener', appliedFilters],
    queryFn: () => screenerApi.screen(buildParams(appliedFilters)).then((r) => r.data),
  });

  const results: ScreenerResult[] = data?.results ?? [];
  const totalMatches = data?.meta?.total_matches ?? 0;

  const handleApply = () => {
    setAppliedFilters({ ...filters });
  };

  const handleReset = () => {
    setFilters(defaultFilters);
    setAppliedFilters(defaultFilters);
  };

  const updateFilter = <K extends keyof Filters>(key: K, value: Filters[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const columns: Column[] = [
    {
      key: 'symbol',
      label: 'Symbol',
      sortable: true,
      render: (val: string) => (
        <span className="font-semibold text-blue-400">{val}</span>
      ),
    },
    { key: 'name', label: 'Name', sortable: true },
    { key: 'sector', label: 'Sector', sortable: true },
    {
      key: 'last_price',
      label: 'Price',
      sortable: true,
      align: 'right',
      render: (val: number) => (
        <span className="font-mono">{formatPrice(val)}</span>
      ),
    },
    {
      key: 'change_pct',
      label: 'Change %',
      sortable: true,
      align: 'right',
      render: (val: number) => (
        <span
          className={`font-mono font-medium ${
            val > 0 ? 'text-emerald-400' : val < 0 ? 'text-red-400' : 'text-slate-400'
          }`}
        >
          {val > 0 ? '+' : ''}
          {val?.toFixed(2) ?? '--'}%
        </span>
      ),
    },
    {
      key: 'volume',
      label: 'Volume',
      sortable: true,
      align: 'right',
      render: (val: number) => (
        <span className="font-mono">{val ? formatNumber(val) : '--'}</span>
      ),
    },
    {
      key: 'market_cap',
      label: 'Market Cap',
      sortable: true,
      align: 'right',
      render: (val: number) => (
        <span className="font-mono">{val ? formatNumber(val) : '--'}</span>
      ),
    },
    {
      key: 'pe_ratio',
      label: 'P/E',
      sortable: true,
      align: 'right',
      render: (val: number | null) => (
        <span className="font-mono">{val != null ? val.toFixed(2) : '--'}</span>
      ),
    },
    {
      key: 'pbv_ratio',
      label: 'P/BV',
      sortable: true,
      align: 'right',
      render: (val: number | null) => (
        <span className="font-mono">{val != null ? val.toFixed(2) : '--'}</span>
      ),
    },
    {
      key: 'roe',
      label: 'ROE',
      sortable: true,
      align: 'right',
      render: (val: number | null) => (
        <span className="font-mono">{val != null ? val.toFixed(2) + '%' : '--'}</span>
      ),
    },
    {
      key: 'dividend_yield',
      label: 'Div Yield',
      sortable: true,
      align: 'right',
      render: (val: number | null) => (
        <span className="font-mono">{val != null ? val.toFixed(2) + '%' : '--'}</span>
      ),
    },
    {
      key: 'is_lq45',
      label: 'LQ45',
      render: (val: boolean) => (val ? <Badge variant="info">LQ45</Badge> : null),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Equity Screener" subtitle="Filter and discover Indonesian equities" />

      {/* Filter Panel */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {/* Sector */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Sector</label>
            <select
              value={filters.sector}
              onChange={(e) => updateFilter('sector', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Sectors</option>
              {SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Market Cap Min */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Market Cap Min
            </label>
            <input
              type="number"
              placeholder="e.g. 1000000000"
              value={filters.min_market_cap}
              onChange={(e) => updateFilter('min_market_cap', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Market Cap Max */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Market Cap Max
            </label>
            <input
              type="number"
              placeholder="e.g. 100000000000"
              value={filters.max_market_cap}
              onChange={(e) => updateFilter('max_market_cap', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* PE Min */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">P/E Min</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 5"
              value={filters.min_pe}
              onChange={(e) => updateFilter('min_pe', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* PE Max */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">P/E Max</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 25"
              value={filters.max_pe}
              onChange={(e) => updateFilter('max_pe', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* PBV Min */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">P/BV Min</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 0.5"
              value={filters.min_pbv}
              onChange={(e) => updateFilter('min_pbv', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* PBV Max */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">P/BV Max</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 5"
              value={filters.max_pbv}
              onChange={(e) => updateFilter('max_pbv', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* ROE Min */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">ROE Min (%)</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 10"
              value={filters.min_roe}
              onChange={(e) => updateFilter('min_roe', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Dividend Yield Min */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Div Yield Min (%)
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 2"
              value={filters.min_dividend_yield}
              onChange={(e) => updateFilter('min_dividend_yield', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Sort By</label>
            <select
              value={filters.sort_by}
              onChange={(e) => updateFilter('sort_by', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Direction */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Direction</label>
            <select
              value={filters.sort_dir}
              onChange={(e) => updateFilter('sort_dir', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>

          {/* LQ45 Toggle + Buttons */}
          <div className="flex flex-col justify-end gap-2">
            <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.lq45_only}
                onChange={(e) => updateFilter('lq45_only', e.target.checked)}
                className="rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              LQ45 Only
            </label>
            <div className="flex gap-2">
              <button
                onClick={handleApply}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              >
                <Search className="h-3.5 w-3.5" />
                Apply
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-md transition-colors"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-slate-100">Results</h3>
          <span className="text-sm text-slate-400">
            {totalMatches.toLocaleString()} match{totalMatches !== 1 ? 'es' : ''} found
          </span>
        </div>
        <DataTable
          columns={columns}
          data={results}
          loading={isLoading}
          onRowClick={(row: ScreenerResult) => navigate(`/stocks/${row.symbol}`)}
          emptyMessage="No stocks match your criteria. Try adjusting the filters."
        />
      </div>
    </div>
  );
}
