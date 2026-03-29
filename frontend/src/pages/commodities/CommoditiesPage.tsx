import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Gem, X, AlertTriangle, Search } from 'lucide-react';
import { commodityApi, commodityImpactApi } from '../../api/endpoints';
import type {
  CommodityPrice,
  CommodityImpactAnalysis,
  ImpactAlert,
} from '../../types';
import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import DataTable from '../../components/common/DataTable';
import type { Column } from '../../components/common/DataTable';

const CATEGORIES = ['All', 'Energy', 'Metals', 'Agriculture'] as const;

function formatNumber(val: number): string {
  if (Math.abs(val) >= 1_000_000_000) return (val / 1_000_000_000).toFixed(1) + 'B';
  if (Math.abs(val) >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M';
  if (Math.abs(val) >= 1_000) return (val / 1_000).toFixed(1) + 'K';
  return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function changePctColor(pct: number): string {
  if (pct > 0) return 'text-emerald-400';
  if (pct < 0) return 'text-red-400';
  return 'text-slate-400';
}

function categoryForCommodity(code: string): string {
  const lower = code.toLowerCase();
  if (
    lower.includes('oil') ||
    lower.includes('gas') ||
    lower.includes('coal') ||
    lower.includes('brent') ||
    lower.includes('wti') ||
    lower.includes('lng')
  )
    return 'Energy';
  if (
    lower.includes('gold') ||
    lower.includes('silver') ||
    lower.includes('copper') ||
    lower.includes('nickel') ||
    lower.includes('tin') ||
    lower.includes('iron') ||
    lower.includes('alumin') ||
    lower.includes('steel')
  )
    return 'Metals';
  if (
    lower.includes('palm') ||
    lower.includes('rubber') ||
    lower.includes('coffee') ||
    lower.includes('cocoa') ||
    lower.includes('sugar') ||
    lower.includes('rice') ||
    lower.includes('corn') ||
    lower.includes('soy') ||
    lower.includes('wheat')
  )
    return 'Agriculture';
  return 'Energy';
}

function severityVariant(severity: string): 'danger' | 'warning' | 'info' | 'neutral' {
  const s = severity.toLowerCase();
  if (s === 'critical' || s === 'high') return 'danger';
  if (s === 'medium') return 'warning';
  if (s === 'low') return 'info';
  return 'neutral';
}

export default function CommoditiesPage() {
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [selectedCommodity, setSelectedCommodity] = useState<string | null>(null);
  const [impactCode, setImpactCode] = useState('');
  const [searchedImpactCode, setSearchedImpactCode] = useState('');

  const { data: commodities, isLoading: loadingCommodities } = useQuery({
    queryKey: ['commodity-prices'],
    queryFn: () => commodityApi.prices().then((r) => r.data),
  });

  const { data: history, isLoading: loadingHistory } = useQuery({
    queryKey: ['commodity-history', selectedCommodity],
    queryFn: () =>
      commodityApi.history(selectedCommodity!, { limit: 90 }).then((r) => r.data),
    enabled: !!selectedCommodity,
  });

  const { data: impactAnalysis, isLoading: loadingImpact } = useQuery({
    queryKey: ['commodity-impact', searchedImpactCode],
    queryFn: () =>
      commodityImpactApi.analysis(searchedImpactCode).then((r) => r.data),
    enabled: !!searchedImpactCode,
  });

  const { data: alerts, isLoading: loadingAlerts } = useQuery({
    queryKey: ['commodity-alerts'],
    queryFn: () => commodityImpactApi.alerts({ limit: 20 }).then((r) => r.data),
  });

  const filtered = commodities?.filter(
    (c: CommodityPrice) =>
      activeCategory === 'All' || categoryForCommodity(c.code) === activeCategory,
  );

  const selectedName = commodities?.find(
    (c: CommodityPrice) => c.code === selectedCommodity,
  )?.name;

  const impactColumns: Column[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    { key: 'name', label: 'Name' },
    { key: 'sector', label: 'Sector' },
    {
      key: 'correlation',
      label: 'Correlation',
      align: 'right',
      sortable: true,
      render: (v: number) => (
        <span className={v > 0 ? 'text-emerald-400' : 'text-red-400'}>
          {v.toFixed(3)}
        </span>
      ),
    },
    {
      key: 'beta',
      label: 'Beta',
      align: 'right',
      sortable: true,
      render: (v: number) => v.toFixed(3),
    },
    {
      key: 'revenue_exposure_pct',
      label: 'Revenue Exposure',
      align: 'right',
      sortable: true,
      render: (v: number) => `${v.toFixed(1)}%`,
    },
  ];

  return (
    <div>
      <PageHeader title="Commodities" subtitle="Global commodity prices and IDX impact analysis">
        <Gem className="h-5 w-5 text-slate-400" />
      </PageHeader>

      {/* Category tabs */}
      <div className="flex items-center gap-1 mb-6 bg-slate-800/50 p-1 rounded-lg w-fit">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeCategory === cat
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Commodity price cards */}
      {loadingCommodities ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner label="Loading commodities..." />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
          {filtered?.map((c: CommodityPrice) => (
            <button
              key={c.code}
              onClick={() =>
                setSelectedCommodity(selectedCommodity === c.code ? null : c.code)
              }
              className={`p-4 text-left rounded-lg border transition-colors ${
                selectedCommodity === c.code
                  ? 'bg-blue-500/10 border-blue-500/40'
                  : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
              }`}
            >
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                {c.name}
              </p>
              <p className="text-xl font-bold text-slate-100">
                {formatNumber(c.last_price)}{' '}
                <span className="text-xs font-normal text-slate-500">
                  {c.currency}/{c.unit}
                </span>
              </p>
              <div className="flex items-center gap-3 mt-2 text-xs">
                <span className={changePctColor(c.change_pct)}>
                  {c.change_pct >= 0 ? '+' : ''}
                  {c.change_pct.toFixed(2)}%
                </span>
                <span className="text-slate-600">|</span>
                <span className={`${changePctColor(c.change_1w_pct)}`}>
                  1W: {c.change_1w_pct >= 0 ? '+' : ''}
                  {c.change_1w_pct.toFixed(2)}%
                </span>
                <span className={`${changePctColor(c.change_1m_pct)}`}>
                  1M: {c.change_1m_pct >= 0 ? '+' : ''}
                  {c.change_1m_pct.toFixed(2)}%
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Price History Chart */}
      {selectedCommodity && (
        <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-100">
              {selectedName} - Price History
            </h3>
            <button
              onClick={() => setSelectedCommodity(null)}
              className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          {loadingHistory ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="sm" />
            </div>
          ) : history && history.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  tickFormatter={(d: string) => format(new Date(d), 'MMM dd')}
                />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: 12,
                  }}
                  labelFormatter={(d: any) => format(new Date(d), 'MMM dd, yyyy')}
                  formatter={(value: any) => [formatNumber(Number(value)), 'Price']}
                />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#priceGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">
              No history data available.
            </p>
          )}
        </div>
      )}

      {/* Impact Analysis */}
      <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <h3 className="text-sm font-semibold text-slate-100 mb-4">
          Commodity Impact Analysis
        </h3>
        <div className="flex items-center gap-3 mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Commodity code (e.g. COAL)"
              value={impactCode}
              onChange={(e) => setImpactCode(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && impactCode.trim()) {
                  setSearchedImpactCode(impactCode.trim());
                }
              }}
              className="pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-56"
            />
          </div>
          <button
            onClick={() => {
              if (impactCode.trim()) setSearchedImpactCode(impactCode.trim());
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Analyze
          </button>
        </div>

        {loadingImpact ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" label="Analyzing impact..." />
          </div>
        ) : impactAnalysis ? (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <span className="text-sm text-slate-300">
                {(impactAnalysis as CommodityImpactAnalysis).commodity_name}
              </span>
              <span
                className={`text-sm font-medium ${changePctColor(
                  (impactAnalysis as CommodityImpactAnalysis).change_pct_30d,
                )}`}
              >
                30d:{' '}
                {(impactAnalysis as CommodityImpactAnalysis).change_pct_30d >= 0
                  ? '+'
                  : ''}
                {(impactAnalysis as CommodityImpactAnalysis).change_pct_30d.toFixed(2)}%
              </span>
            </div>
            <DataTable
              columns={impactColumns}
              data={
                (impactAnalysis as CommodityImpactAnalysis).impacted_stocks || []
              }
              emptyMessage="No impacted stocks found."
            />
          </div>
        ) : searchedImpactCode ? (
          <p className="text-sm text-slate-500 text-center py-4">
            No impact data found for {searchedImpactCode}.
          </p>
        ) : (
          <p className="text-xs text-slate-500 text-center py-4">
            Enter a commodity code and click Analyze to see impacted IDX stocks.
          </p>
        )}
      </div>

      {/* Alerts Panel */}
      <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-100">
            Recent Impact Alerts
          </h3>
        </div>
        {loadingAlerts ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        ) : !alerts || alerts.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No recent alerts.</p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert: ImpactAlert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 p-3 bg-slate-900/50 border border-slate-700/50 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={severityVariant(alert.severity)}>
                      {alert.severity}
                    </Badge>
                    <span className="text-xs text-slate-500">
                      {alert.commodity_name} &middot; {alert.symbol}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300">{alert.message}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {format(new Date(alert.created_at), 'MMM dd, yyyy HH:mm')}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
