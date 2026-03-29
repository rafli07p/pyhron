import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Landmark } from 'lucide-react';
import { fixedIncomeApi } from '../../api/endpoints';
import type {
  GovernmentBond,
  CreditSpread,
} from '../../types';
import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import DataTable from '../../components/common/DataTable';
import type { Column } from '../../components/common/DataTable';

const TABS = ['Government Bonds', 'Corporate Bonds', 'Yield Curve', 'Credit Spreads'] as const;
type Tab = (typeof TABS)[number];

function formatBillion(val: number): string {
  if (Math.abs(val) >= 1_000_000_000_000) return (val / 1_000_000_000_000).toFixed(2) + 'T';
  if (Math.abs(val) >= 1_000_000_000) return (val / 1_000_000_000).toFixed(2) + 'B';
  if (Math.abs(val) >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M';
  return val.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function ratingBadgeVariant(rating: string): 'success' | 'info' | 'warning' | 'danger' | 'neutral' {
  const r = rating.toUpperCase();
  if (r.startsWith('AAA') || r.startsWith('AA')) return 'success';
  if (r.startsWith('A')) return 'info';
  if (r.startsWith('BBB')) return 'warning';
  if (r.startsWith('BB') || r.startsWith('B')) return 'danger';
  return 'neutral';
}

export default function FixedIncomePage() {
  const [activeTab, setActiveTab] = useState<Tab>('Government Bonds');
  const [govBondType, setGovBondType] = useState('');
  const [govMinTenor, setGovMinTenor] = useState('');
  const [govMaxTenor, setGovMaxTenor] = useState('');
  const [corpRating, setCorpRating] = useState('');
  const [corpIssuer, setCorpIssuer] = useState('');
  const [ycBondType, setYcBondType] = useState('SUN');

  // Government Bonds query
  const { data: govBonds, isLoading: loadingGov } = useQuery({
    queryKey: ['gov-bonds', govBondType, govMinTenor, govMaxTenor],
    queryFn: () =>
      fixedIncomeApi
        .governmentBonds({
          bond_type: govBondType || undefined,
          min_tenor: govMinTenor ? Number(govMinTenor) : undefined,
          max_tenor: govMaxTenor ? Number(govMaxTenor) : undefined,
        })
        .then((r) => r.data),
    enabled: activeTab === 'Government Bonds',
  });

  // Corporate Bonds query
  const { data: corpBonds, isLoading: loadingCorp } = useQuery({
    queryKey: ['corp-bonds', corpRating, corpIssuer],
    queryFn: () =>
      fixedIncomeApi
        .corporateBonds({
          rating: corpRating || undefined,
          issuer_symbol: corpIssuer || undefined,
          limit: 100,
        })
        .then((r) => r.data),
    enabled: activeTab === 'Corporate Bonds',
  });

  // Yield curve: fetch government bonds filtered by type, then plot by duration
  const { data: govBondsForYC, isLoading: loadingYC } = useQuery({
    queryKey: ['gov-bonds-yc', ycBondType],
    queryFn: () =>
      fixedIncomeApi
        .governmentBonds({ bond_type: ycBondType })
        .then((r) => r.data),
    enabled: activeTab === 'Yield Curve',
  });

  // Credit Spreads query
  const { data: creditSpreads, isLoading: loadingSpreads } = useQuery({
    queryKey: ['credit-spreads'],
    queryFn: () => fixedIncomeApi.creditSpreads().then((r) => r.data),
    enabled: activeTab === 'Credit Spreads',
  });

  // Build yield curve data sorted by duration
  const yieldCurveData = govBondsForYC
    ? [...govBondsForYC]
        .sort((a: GovernmentBond, b: GovernmentBond) => a.duration - b.duration)
        .map((bond: GovernmentBond) => ({
          tenor: bond.duration.toFixed(1) + 'Y',
          duration: bond.duration,
          yield_pct: bond.yield_to_maturity,
          series: bond.series,
        }))
    : [];

  const govColumns: Column[] = [
    { key: 'series', label: 'Series', sortable: true },
    {
      key: 'bond_type',
      label: 'Type',
      sortable: true,
      render: (v: string) => <Badge variant="info">{v}</Badge>,
    },
    {
      key: 'coupon_rate',
      label: 'Coupon',
      align: 'right',
      sortable: true,
      render: (v: number) => `${v.toFixed(2)}%`,
    },
    {
      key: 'maturity_date',
      label: 'Maturity',
      sortable: true,
      render: (v: string) => format(new Date(v), 'dd MMM yyyy'),
    },
    {
      key: 'yield_to_maturity',
      label: 'YTM',
      align: 'right',
      sortable: true,
      render: (v: number) => (
        <span className="font-medium text-blue-400">{v.toFixed(2)}%</span>
      ),
    },
    {
      key: 'price',
      label: 'Price',
      align: 'right',
      sortable: true,
      render: (v: number) => v.toFixed(2),
    },
    {
      key: 'duration',
      label: 'Duration',
      align: 'right',
      sortable: true,
      render: (v: number) => v.toFixed(2),
    },
    {
      key: 'outstanding',
      label: 'Outstanding',
      align: 'right',
      sortable: true,
      render: (v: number) => formatBillion(v),
    },
  ];

  const corpColumns: Column[] = [
    { key: 'series', label: 'Series', sortable: true },
    { key: 'issuer', label: 'Issuer', sortable: true },
    {
      key: 'rating',
      label: 'Rating',
      sortable: true,
      render: (v: string) => <Badge variant={ratingBadgeVariant(v)}>{v}</Badge>,
    },
    {
      key: 'coupon_rate',
      label: 'Coupon',
      align: 'right',
      sortable: true,
      render: (v: number) => `${v.toFixed(2)}%`,
    },
    {
      key: 'maturity_date',
      label: 'Maturity',
      sortable: true,
      render: (v: string) => format(new Date(v), 'dd MMM yyyy'),
    },
    {
      key: 'yield_to_maturity',
      label: 'YTM',
      align: 'right',
      sortable: true,
      render: (v: number) => (
        <span className="font-medium text-blue-400">{v.toFixed(2)}%</span>
      ),
    },
    {
      key: 'price',
      label: 'Price',
      align: 'right',
      sortable: true,
      render: (v: number) => v.toFixed(2),
    },
  ];

  const spreadColumns: Column[] = [
    {
      key: 'rating',
      label: 'Rating',
      sortable: true,
      render: (v: string) => <Badge variant={ratingBadgeVariant(v)}>{v}</Badge>,
    },
    { key: 'tenor', label: 'Tenor', sortable: true },
    {
      key: 'spread_bps',
      label: 'Spread (bps)',
      align: 'right',
      sortable: true,
      render: (v: number) => (
        <span className="font-medium text-slate-200">{v.toFixed(0)}</span>
      ),
    },
    {
      key: 'change_bps',
      label: 'Change (bps)',
      align: 'right',
      sortable: true,
      render: (v: number) => (
        <span
          className={
            v > 0 ? 'text-red-400' : v < 0 ? 'text-emerald-400' : 'text-slate-400'
          }
        >
          {v > 0 ? '+' : ''}
          {v.toFixed(1)}
        </span>
      ),
    },
    {
      key: 'benchmark_yield',
      label: 'Benchmark Yield',
      align: 'right',
      sortable: true,
      render: (v: number) => `${v.toFixed(2)}%`,
    },
  ];

  // Build chart data for credit spreads by rating across tenors
  const spreadChartData = creditSpreads
    ? (() => {
        const ratings = [...new Set(creditSpreads.map((s: CreditSpread) => s.rating))];
        const tenors = [...new Set(creditSpreads.map((s: CreditSpread) => s.tenor))];
        return tenors.map((tenor) => {
          const point: Record<string, string | number> = { tenor };
          ratings.forEach((rating) => {
            const found = creditSpreads.find(
              (s: CreditSpread) => s.tenor === tenor && s.rating === rating,
            );
            if (found) point[rating] = found.spread_bps;
          });
          return point;
        });
      })()
    : [];

  const spreadRatings = creditSpreads
    ? [...new Set(creditSpreads.map((s: CreditSpread) => s.rating))]
    : [];

  const SPREAD_COLORS = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#ec4899',
  ];

  return (
    <div>
      <PageHeader
        title="Fixed Income"
        subtitle="Indonesian government and corporate bond markets"
      >
        <Landmark className="h-5 w-5 text-slate-400" />
      </PageHeader>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6 bg-slate-800/50 p-1 rounded-lg w-fit">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Government Bonds Tab */}
      {activeTab === 'Government Bonds' && (
        <div>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <select
              value={govBondType}
              onChange={(e) => setGovBondType(e.target.value)}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Types</option>
              <option value="SUN">SUN</option>
              <option value="SBSN">SBSN</option>
              <option value="SPN">SPN</option>
            </select>
            <input
              type="number"
              placeholder="Min tenor (yrs)"
              value={govMinTenor}
              onChange={(e) => setGovMinTenor(e.target.value)}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-36"
            />
            <input
              type="number"
              placeholder="Max tenor (yrs)"
              value={govMaxTenor}
              onChange={(e) => setGovMaxTenor(e.target.value)}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-36"
            />
          </div>
          <DataTable
            columns={govColumns}
            data={govBonds || []}
            loading={loadingGov}
            emptyMessage="No government bonds found."
          />
        </div>
      )}

      {/* Corporate Bonds Tab */}
      {activeTab === 'Corporate Bonds' && (
        <div>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <select
              value={corpRating}
              onChange={(e) => setCorpRating(e.target.value)}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Ratings</option>
              <option value="AAA">AAA</option>
              <option value="AA+">AA+</option>
              <option value="AA">AA</option>
              <option value="AA-">AA-</option>
              <option value="A+">A+</option>
              <option value="A">A</option>
              <option value="A-">A-</option>
              <option value="BBB+">BBB+</option>
              <option value="BBB">BBB</option>
              <option value="BBB-">BBB-</option>
              <option value="BB+">BB+</option>
              <option value="BB">BB</option>
            </select>
            <input
              type="text"
              placeholder="Issuer symbol"
              value={corpIssuer}
              onChange={(e) => setCorpIssuer(e.target.value.toUpperCase())}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-44"
            />
          </div>
          <DataTable
            columns={corpColumns}
            data={corpBonds || []}
            loading={loadingCorp}
            emptyMessage="No corporate bonds found."
          />
        </div>
      )}

      {/* Yield Curve Tab */}
      {activeTab === 'Yield Curve' && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-sm text-slate-400">Bond type:</span>
            {['SUN', 'SBSN'].map((bt) => (
              <button
                key={bt}
                onClick={() => setYcBondType(bt)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  ycBondType === bt
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                    : 'bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                {bt}
              </button>
            ))}
          </div>
          <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
            {loadingYC ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="sm" label="Loading yield curve..." />
              </div>
            ) : yieldCurveData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={yieldCurveData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="tenor"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: 12,
                    }}
                    formatter={(value: any) => [`${Number(value).toFixed(2)}%`, 'Yield']}
                    labelFormatter={(label: any) => `Tenor: ${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="yield_pct"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#10b981' }}
                    name="Yield"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-500 text-center py-8">
                No yield curve data available for {ycBondType}.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Credit Spreads Tab */}
      {activeTab === 'Credit Spreads' && (
        <div className="space-y-6">
          {/* Chart */}
          <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
            <h3 className="text-sm font-semibold text-slate-100 mb-4">
              Credit Spreads by Rating
            </h3>
            {loadingSpreads ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="sm" />
              </div>
            ) : spreadChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={spreadChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="tenor"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    label={{
                      value: 'Spread (bps)',
                      angle: -90,
                      position: 'insideLeft',
                      style: { fill: '#94a3b8', fontSize: 11 },
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: 12,
                    }}
                    formatter={(value: any, name: any) => [
                      `${Number(value).toFixed(0)} bps`,
                      name,
                    ]}
                  />
                  <Legend />
                  {spreadRatings.map((rating, idx) => (
                    <Line
                      key={rating}
                      type="monotone"
                      dataKey={rating}
                      stroke={SPREAD_COLORS[idx % SPREAD_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name={rating}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-500 text-center py-8">
                No credit spread data available.
              </p>
            )}
          </div>

          {/* Table */}
          <DataTable
            columns={spreadColumns}
            data={creditSpreads || []}
            loading={loadingSpreads}
            emptyMessage="No credit spread data available."
          />
        </div>
      )}
    </div>
  );
}
