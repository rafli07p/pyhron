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
import {
  Briefcase,
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import StatCard from '../../components/common/StatCard';
import DataTable from '../../components/common/DataTable';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { tradingApi, strategyApi } from '../../api/endpoints';
import type {
  PositionResponse,
  PnLResponse,
  Strategy,
} from '../../types';

function formatIdr(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1_000_000_000_000) return `${sign}Rp ${(abs / 1_000_000_000_000).toFixed(1)}T`;
  if (abs >= 1_000_000_000) return `${sign}Rp ${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${sign}Rp ${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}Rp ${(abs / 1_000).toFixed(1)}K`;
  return `${sign}Rp ${abs.toFixed(0)}`;
}

export default function PositionsPage() {
  const [strategyFilter, setStrategyFilter] = useState('ALL');

  const { data: positions = [], isLoading: positionsLoading } = useQuery({
    queryKey: ['positions', strategyFilter],
    queryFn: () =>
      tradingApi
        .positions(strategyFilter === 'ALL' ? {} : { strategy_id: strategyFilter })
        .then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: pnlData = [], isLoading: pnlLoading } = useQuery({
    queryKey: ['positions-pnl'],
    queryFn: () => tradingApi.pnl().then((r) => r.data),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list().then((r) => r.data),
  });

  // Summary stats
  const totalMarketValue = positions.reduce(
    (sum: number, p: PositionResponse) => sum + p.market_value,
    0,
  );
  const totalUnrealizedPnl = positions.reduce(
    (sum: number, p: PositionResponse) => sum + p.unrealized_pnl,
    0,
  );
  const latestPnl = pnlData.length > 0 ? pnlData[pnlData.length - 1] : null;
  const totalRealizedPnl = latestPnl ? latestPnl.realized_pnl : 0;
  const dailyReturn = latestPnl ? latestPnl.daily_return_pct : 0;

  // Chart data
  const equityChartData = pnlData.map((d: PnLResponse) => ({
    date: format(new Date(d.date), 'dd MMM'),
    total_equity: d.total_equity,
  }));

  // Strategy IDs from positions for filter
  const strategyIds = Array.from(
    new Set(positions.map((p: PositionResponse) => p.strategy_id)),
  );

  const positionColumns = [
    {
      key: 'symbol',
      label: 'Symbol',
      sortable: true,
      render: (v: string) => (
        <span className="font-semibold text-slate-100">{v}</span>
      ),
    },
    { key: 'strategy_id', label: 'Strategy', sortable: true },
    {
      key: 'quantity',
      label: 'Qty',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => v.toLocaleString('id-ID'),
    },
    {
      key: 'avg_entry_price',
      label: 'Avg Entry',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => v.toLocaleString('id-ID'),
    },
    {
      key: 'current_price',
      label: 'Current',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => v.toLocaleString('id-ID'),
    },
    {
      key: 'unrealized_pnl',
      label: 'Unrealized P&L',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => (
        <span className={`font-medium ${v >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {v >= 0 ? '+' : ''}
          {formatIdr(v)}
        </span>
      ),
    },
    {
      key: 'market_value',
      label: 'Market Value',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => formatIdr(v),
    },
    {
      key: 'weight_pct',
      label: 'Weight',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => `${v.toFixed(2)}%`,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Positions & P&L" subtitle="Portfolio positions and performance" />

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Market Value"
          value={formatIdr(totalMarketValue)}
          icon={Briefcase}
        />
        <StatCard
          title="Unrealized P&L"
          value={`${totalUnrealizedPnl >= 0 ? '+' : ''}${formatIdr(totalUnrealizedPnl)}`}
          change={
            totalMarketValue > 0
              ? (totalUnrealizedPnl / (totalMarketValue - totalUnrealizedPnl)) * 100
              : undefined
          }
          icon={totalUnrealizedPnl >= 0 ? TrendingUp : TrendingDown}
        />
        <StatCard
          title="Realized P&L"
          value={`${totalRealizedPnl >= 0 ? '+' : ''}${formatIdr(totalRealizedPnl)}`}
          icon={DollarSign}
        />
        <StatCard
          title="Daily Return"
          value={`${dailyReturn >= 0 ? '+' : ''}${dailyReturn.toFixed(2)}%`}
          change={dailyReturn}
          changeLabel="today"
          icon={PieChart}
        />
      </div>

      {/* Positions Table */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-slate-100">Positions</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setStrategyFilter('ALL')}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
                strategyFilter === 'ALL'
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
              }`}
            >
              ALL
            </button>
            {strategyIds.map((sid: string) => (
              <button
                key={sid}
                onClick={() => setStrategyFilter(sid)}
                className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
                  strategyFilter === sid
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                }`}
              >
                {strategies.find((s: Strategy) => s.id === sid)?.name ?? sid}
              </button>
            ))}
          </div>
        </div>
        <DataTable
          columns={positionColumns}
          data={positions}
          loading={positionsLoading}
          emptyMessage="No open positions"
        />
      </div>

      {/* P&L Equity Curve */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <h3 className="text-base font-semibold text-slate-100 mb-4">
          Equity Curve
        </h3>
        {pnlLoading ? (
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner label="Loading P&L..." />
          </div>
        ) : equityChartData.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-12">
            No P&L data available yet.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart
              data={equityChartData}
              margin={{ top: 5, right: 10, left: 10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
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
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={false}
                tickFormatter={(v: number) => formatIdr(v)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '0.5rem',
                  color: '#f1f5f9',
                  fontSize: 13,
                }}
                formatter={((value: any) => [formatIdr(value), 'Equity']) as any}
              />
              <Area
                type="monotone"
                dataKey="total_equity"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
