import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import StatCard from '../../components/common/StatCard';
import Badge from '../../components/common/Badge';
import DataTable from '../../components/common/DataTable';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import type { Column } from '../../components/common/DataTable';
import { marketApi } from '../../api/endpoints';
import type { OHLCVBar, Instrument } from '../../types';

const INTERVALS = [
  { label: '1D', interval: '5m', limit: 78 },
  { label: '1W', interval: '1h', limit: 35 },
  { label: '1M', interval: '1d', limit: 22 },
  { label: '3M', interval: '1d', limit: 66 },
  { label: '1Y', interval: '1w', limit: 52 },
] as const;

function formatNumber(value: number): string {
  if (value >= 1_000_000_000_000) return (value / 1_000_000_000_000).toFixed(2) + 'T';
  if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(2) + 'B';
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(2) + 'M';
  if (value >= 1_000) return (value / 1_000).toFixed(2) + 'K';
  return value.toFixed(2);
}

function formatPrice(value: number): string {
  return value.toLocaleString('id-ID', { maximumFractionDigits: 2 });
}

export default function MarketOverviewPage() {
  const navigate = useNavigate();
  const [selectedInterval, setSelectedInterval] = useState(2); // default 1M
  const [sectorFilter, setSectorFilter] = useState('');
  const [lq45Only, setLq45Only] = useState(false);

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['market-overview'],
    queryFn: () => marketApi.overview().then((r) => r.data),
  });

  const currentInterval = INTERVALS[selectedInterval];

  const { data: ohlcvData, isLoading: chartLoading } = useQuery({
    queryKey: ['ihsg-ohlcv', currentInterval.interval, currentInterval.limit],
    queryFn: () =>
      marketApi
        .ohlcv('IHSG', {
          interval: currentInterval.interval,
          limit: currentInterval.limit,
        })
        .then((r) => r.data),
  });

  const { data: instruments, isLoading: instrumentsLoading } = useQuery({
    queryKey: ['instruments', sectorFilter, lq45Only],
    queryFn: () =>
      marketApi
        .instruments({
          ...(sectorFilter ? { sector: sectorFilter } : {}),
          ...(lq45Only ? { lq45_only: true } : {}),
        })
        .then((r) => r.data),
  });

  const chartData = (ohlcvData ?? []).map((bar: OHLCVBar) => {
    const d = new Date(bar.timestamp);
    let dateLabel: string;
    if (currentInterval.interval === '5m' || currentInterval.interval === '1h') {
      dateLabel = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    } else {
      dateLabel = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
    }
    return { date: dateLabel, close: bar.close, volume: bar.volume };
  });

  // Extract unique sectors from instruments
  const sectors = Array.from(
    new Set((instruments ?? []).map((i: Instrument) => i.sector).filter(Boolean))
  ).sort();

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
      key: 'market_cap',
      label: 'Market Cap',
      sortable: true,
      align: 'right',
      render: (val: number) => (
        <span className="font-mono">{val ? formatNumber(val) : '--'}</span>
      ),
    },
    {
      key: 'is_lq45',
      label: 'LQ45',
      render: (val: boolean) =>
        val ? <Badge variant="info">LQ45</Badge> : null,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Market Overview" subtitle="Indonesian equity market summary" />

      {/* Market Stats Row */}
      {overviewLoading ? (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner label="Loading market data..." />
        </div>
      ) : overview ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            title="IHSG"
            value={formatPrice(overview.last_value)}
            change={overview.change_pct}
            changeLabel="today"
          />
          <StatCard
            title="Change"
            value={`${overview.change >= 0 ? '+' : ''}${overview.change.toFixed(2)}`}
            icon={overview.change >= 0 ? TrendingUp : TrendingDown}
          />
          <StatCard title="Volume" value={formatNumber(overview.volume)} />
          <StatCard
            title="Advances"
            value={overview.advances.toString()}
            icon={ArrowUpRight}
          />
          <StatCard
            title="Declines"
            value={overview.declines.toString()}
            icon={ArrowDownRight}
          />
          <StatCard
            title="Unchanged"
            value={overview.unchanged.toString()}
            icon={Minus}
          />
        </div>
      ) : null}

      {/* IHSG Chart */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-slate-100">IHSG Index</h3>
          <div className="flex gap-1">
            {INTERVALS.map((intv, idx) => (
              <button
                key={intv.label}
                onClick={() => setSelectedInterval(idx)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  selectedInterval === idx
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                {intv.label}
              </button>
            ))}
          </div>
        </div>
        {chartLoading ? (
          <div className="flex items-center justify-center h-80">
            <LoadingSpinner label="Loading chart..." />
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="ihsgOverviewGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={false}
                tickFormatter={(v: number) => formatPrice(v)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '0.5rem',
                  color: '#f1f5f9',
                  fontSize: 13,
                }}
                formatter={(value) => [formatPrice(Number(value)), 'Close']}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#ihsgOverviewGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Instruments Table */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <h3 className="text-base font-semibold text-slate-100">Instruments</h3>
          <div className="flex items-center gap-3">
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="px-3 py-1.5 text-sm bg-slate-900 border border-slate-700 rounded-md text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Sectors</option>
              {sectors.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={lq45Only}
                onChange={(e) => setLq45Only(e.target.checked)}
                className="rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              LQ45 Only
            </label>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={instruments ?? []}
          loading={instrumentsLoading}
          onRowClick={(row: Instrument) => navigate(`/stocks/${row.symbol}`)}
          emptyMessage="No instruments found."
        />
      </div>
    </div>
  );
}
