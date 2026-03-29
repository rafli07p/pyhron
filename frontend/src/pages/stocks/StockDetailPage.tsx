import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  ComposedChart,
  Line,
} from 'recharts';
import {
  TrendingUp,
  Building2,
  DollarSign,
  BarChart3,
  Layers,
  Users,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import StatCard from '../../components/common/StatCard';
import Badge from '../../components/common/Badge';
import DataTable from '../../components/common/DataTable';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import type { Column } from '../../components/common/DataTable';
import { stockApi, marketApi } from '../../api/endpoints';
import type {
  OHLCVBar,
  OwnershipEntry,
} from '../../types';

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

function formatCurrency(value: number): string {
  return 'Rp ' + value.toLocaleString('id-ID', { maximumFractionDigits: 0 });
}

const CHART_INTERVALS = [
  { label: '1D', interval: '5m', limit: 78 },
  { label: '1W', interval: '1h', limit: 35 },
  { label: '1M', interval: '1d', limit: 22 },
  { label: '3M', interval: '1d', limit: 66 },
  { label: '1Y', interval: '1w', limit: 52 },
] as const;

const TABS = ['Chart', 'Financials', 'Corporate Actions', 'Ownership'] as const;
type Tab = (typeof TABS)[number];

const PIE_COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
  '#f97316',
  '#6366f1',
];

export default function StockDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('Chart');
  const [chartInterval, setChartInterval] = useState(2); // default 1M

  // Profile - always fetched
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['stock-profile', symbol],
    queryFn: () => stockApi.profile(symbol!).then((r) => r.data),
    enabled: !!symbol,
  });

  // OHLCV - fetched when Chart tab active
  const currentInterval = CHART_INTERVALS[chartInterval];
  const { data: ohlcvData, isLoading: chartLoading } = useQuery({
    queryKey: ['stock-ohlcv', symbol, currentInterval.interval, currentInterval.limit],
    queryFn: () =>
      marketApi
        .ohlcv(symbol!, {
          interval: currentInterval.interval,
          limit: currentInterval.limit,
        })
        .then((r) => r.data),
    enabled: !!symbol && activeTab === 'Chart',
  });

  // Financials - fetched when Financials tab active
  const { data: financials, isLoading: financialsLoading } = useQuery({
    queryKey: ['stock-financials', symbol],
    queryFn: () => stockApi.financials(symbol!, { limit: 20 }).then((r) => r.data),
    enabled: !!symbol && activeTab === 'Financials',
  });

  // Corporate Actions - fetched when tab active
  const { data: corporateActions, isLoading: caLoading } = useQuery({
    queryKey: ['stock-corporate-actions', symbol],
    queryFn: () => stockApi.corporateActions(symbol!, { limit: 20 }).then((r) => r.data),
    enabled: !!symbol && activeTab === 'Corporate Actions',
  });

  // Ownership - fetched when tab active
  const { data: ownership, isLoading: ownershipLoading } = useQuery({
    queryKey: ['stock-ownership', symbol],
    queryFn: () => stockApi.ownership(symbol!).then((r) => r.data),
    enabled: !!symbol && activeTab === 'Ownership',
  });

  if (profileLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner label="Loading stock data..." size="lg" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-slate-400">Stock not found.</p>
      </div>
    );
  }

  // Chart data
  const chartData = (ohlcvData ?? []).map((bar: OHLCVBar) => {
    const d = new Date(bar.timestamp);
    let dateLabel: string;
    if (currentInterval.interval === '5m' || currentInterval.interval === '1h') {
      dateLabel = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    } else {
      dateLabel = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
    }
    return {
      date: dateLabel,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume,
    };
  });

  // Financial columns
  const financialColumns: Column[] = [
    { key: 'period', label: 'Period', sortable: true },
    {
      key: 'revenue',
      label: 'Revenue',
      sortable: true,
      align: 'right',
      render: (val: number) => <span className="font-mono">{formatNumber(val)}</span>,
    },
    {
      key: 'net_income',
      label: 'Net Income',
      sortable: true,
      align: 'right',
      render: (val: number) => (
        <span className={`font-mono ${val >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {formatNumber(val)}
        </span>
      ),
    },
    {
      key: 'eps',
      label: 'EPS',
      sortable: true,
      align: 'right',
      render: (val: number) => <span className="font-mono">{val?.toFixed(2) ?? '--'}</span>,
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
      key: 'der',
      label: 'DER',
      sortable: true,
      align: 'right',
      render: (val: number | null) => (
        <span className="font-mono">{val != null ? val.toFixed(2) : '--'}</span>
      ),
    },
  ];

  // Corporate action columns
  const caColumns: Column[] = [
    {
      key: 'action_type',
      label: 'Type',
      sortable: true,
      render: (val: string) => {
        const variant =
          val === 'dividend'
            ? 'success'
            : val === 'stock_split'
              ? 'info'
              : val === 'rights_issue'
                ? 'warning'
                : 'neutral';
        return <Badge variant={variant}>{val.replace(/_/g, ' ')}</Badge>;
      },
    },
    {
      key: 'ex_date',
      label: 'Ex Date',
      sortable: true,
      render: (val: string) => format(new Date(val), 'dd MMM yyyy'),
    },
    { key: 'description', label: 'Description' },
    {
      key: 'value',
      label: 'Value',
      align: 'right',
      render: (val: number | null) => (
        <span className="font-mono">{val != null ? formatPrice(val) : '--'}</span>
      ),
    },
  ];

  // Ownership columns
  const ownershipColumns: Column[] = [
    { key: 'holder_name', label: 'Holder', sortable: true },
    {
      key: 'holder_type',
      label: 'Type',
      render: (val: string) => <Badge variant="neutral">{val}</Badge>,
    },
    {
      key: 'shares_held',
      label: 'Shares',
      sortable: true,
      align: 'right',
      render: (val: number) => <span className="font-mono">{formatNumber(val)}</span>,
    },
    {
      key: 'ownership_pct',
      label: 'Ownership %',
      sortable: true,
      align: 'right',
      render: (val: number) => <span className="font-mono">{val.toFixed(2)}%</span>,
    },
    {
      key: 'change_from_prior',
      label: 'Change',
      align: 'right',
      render: (val: number | null) => {
        if (val == null) return <span className="text-slate-500">--</span>;
        return (
          <span
            className={`font-mono font-medium ${
              val > 0 ? 'text-emerald-400' : val < 0 ? 'text-red-400' : 'text-slate-400'
            }`}
          >
            {val > 0 ? '+' : ''}
            {val.toFixed(2)}%
          </span>
        );
      },
    },
  ];

  // Ownership pie data
  const pieData = (ownership ?? []).map((entry: OwnershipEntry) => ({
    name: entry.holder_name.length > 20 ? entry.holder_name.slice(0, 20) + '...' : entry.holder_name,
    value: entry.ownership_pct,
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${profile.symbol} - ${profile.name}`}
        subtitle={`${profile.sector} | ${profile.exchange}${profile.is_lq45 ? ' | LQ45' : ''}`}
      >
        {profile.is_lq45 && <Badge variant="info">LQ45</Badge>}
      </PageHeader>

      {/* Top Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          title="Last Price"
          value={formatCurrency(profile.last_price)}
          icon={DollarSign}
        />
        <StatCard
          title="Market Cap"
          value={formatNumber(profile.market_cap)}
          icon={Building2}
        />
        <StatCard
          title="Shares Outstanding"
          value={formatNumber(profile.shares_outstanding)}
          icon={Layers}
        />
        <StatCard
          title="Sector"
          value={profile.sector}
          icon={BarChart3}
        />
        <StatCard
          title="Industry"
          value={profile.industry}
          icon={TrendingUp}
        />
        <StatCard
          title="Listed"
          value={format(new Date(profile.listing_date), 'dd MMM yyyy')}
          icon={Users}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700">
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-600'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'Chart' && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-slate-100">Price Chart</h3>
            <div className="flex gap-1">
              {CHART_INTERVALS.map((intv, idx) => (
                <button
                  key={intv.label}
                  onClick={() => setChartInterval(idx)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    chartInterval === idx
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
            <div className="flex items-center justify-center h-96">
              <LoadingSpinner label="Loading chart..." />
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-96">
              <p className="text-slate-500">No chart data available.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Price chart with high/low range and close line */}
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
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
                    yAxisId="price"
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
                    formatter={(value: any, name: any) => {
                      const labels: Record<string, string> = {
                        close: 'Close',
                        high: 'High',
                        low: 'Low',
                        open: 'Open',
                      };
                      return [formatPrice(Number(value)), labels[name] || name];
                    }}
                  />
                  <Area
                    yAxisId="price"
                    type="monotone"
                    dataKey="close"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fill="url(#priceGradient)"
                  />
                  <Line
                    yAxisId="price"
                    type="monotone"
                    dataKey="high"
                    stroke="#10b981"
                    strokeWidth={1}
                    strokeDasharray="3 3"
                    dot={false}
                  />
                  <Line
                    yAxisId="price"
                    type="monotone"
                    dataKey="low"
                    stroke="#ef4444"
                    strokeWidth={1}
                    strokeDasharray="3 3"
                    dot={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>

              {/* Volume chart */}
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={chartData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    axisLine={{ stroke: '#475569' }}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    axisLine={{ stroke: '#475569' }}
                    tickLine={false}
                    tickFormatter={(v: number) => formatNumber(v)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #475569',
                      borderRadius: '0.5rem',
                      color: '#f1f5f9',
                      fontSize: 12,
                    }}
                    formatter={(value: any) => [formatNumber(Number(value)), 'Volume']}
                  />
                  <Bar dataKey="volume" fill="#475569" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {activeTab === 'Financials' && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">Financial Summary</h3>
          <DataTable
            columns={financialColumns}
            data={financials ?? []}
            loading={financialsLoading}
            emptyMessage="No financial data available."
          />
        </div>
      )}

      {activeTab === 'Corporate Actions' && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">Corporate Actions</h3>
          <DataTable
            columns={caColumns}
            data={corporateActions ?? []}
            loading={caLoading}
            emptyMessage="No corporate actions recorded."
          />
        </div>
      )}

      {activeTab === 'Ownership' && (
        <div className="space-y-6">
          {/* Pie Chart */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">
              Ownership Distribution
            </h3>
            {ownershipLoading ? (
              <div className="flex items-center justify-center h-72">
                <LoadingSpinner label="Loading ownership..." />
              </div>
            ) : pieData.length === 0 ? (
              <p className="text-sm text-slate-500">No ownership data available.</p>
            ) : (
              <ResponsiveContainer width="100%" height={360}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={80}
                    outerRadius={140}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, value }: any) =>
                      `${name} (${Number(value).toFixed(1)}%)`
                    }
                    labelLine={{ stroke: '#64748b' }}
                  >
                    {pieData.map((_: unknown, index: number) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                        stroke="#1e293b"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #475569',
                      borderRadius: '0.5rem',
                      color: '#f1f5f9',
                      fontSize: 13,
                    }}
                    formatter={(value: any) => [`${Number(value).toFixed(2)}%`, 'Ownership']}
                  />
                  <Legend
                    wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
                    iconType="circle"
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Ownership Table */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">Shareholder Details</h3>
            <DataTable
              columns={ownershipColumns}
              data={ownership ?? []}
              loading={ownershipLoading}
              emptyMessage="No ownership data available."
            />
          </div>
        </div>
      )}
    </div>
  );
}
