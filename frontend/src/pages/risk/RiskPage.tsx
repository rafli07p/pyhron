import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  ShieldOff,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  Activity,
  Target,
  TrendingDown,
  Wallet,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import StatCard from '../../components/common/StatCard';
import Badge from '../../components/common/Badge';
import DataTable from '../../components/common/DataTable';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { riskApi, strategyApi } from '../../api/endpoints';
import type {
  CapitalAllocation,
  RiskHistoryPoint,
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

const PIE_COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#ec4899',
  '#14b8a6',
];

function killSwitchBadgeVariant(
  state: string,
): 'success' | 'danger' | 'warning' | 'neutral' {
  switch (state.toUpperCase()) {
    case 'ARMED':
      return 'success';
    case 'TRIGGERED':
      return 'danger';
    case 'DISARMED':
      return 'warning';
    default:
      return 'neutral';
  }
}

function killSwitchColor(state: string): string {
  switch (state.toUpperCase()) {
    case 'ARMED':
      return 'text-emerald-400';
    case 'TRIGGERED':
      return 'text-red-400';
    case 'DISARMED':
      return 'text-amber-400';
    default:
      return 'text-slate-400';
  }
}

function killSwitchBg(state: string): string {
  switch (state.toUpperCase()) {
    case 'ARMED':
      return 'bg-emerald-500';
    case 'TRIGGERED':
      return 'bg-red-500 animate-pulse';
    case 'DISARMED':
      return 'bg-amber-500';
    default:
      return 'bg-slate-500';
  }
}

export default function RiskPage() {
  const queryClient = useQueryClient();
  const [triggerReason, setTriggerReason] = useState('');
  const [showTriggerConfirm, setShowTriggerConfirm] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('');

  // Kill Switch
  const { data: killSwitch, isLoading: ksLoading } = useQuery({
    queryKey: ['kill-switch'],
    queryFn: () => riskApi.killSwitch().then((r) => r.data),
    refetchInterval: 5000,
  });

  // Capital Allocations
  const { data: capitalData, isLoading: capitalLoading } = useQuery({
    queryKey: ['capital-allocations'],
    queryFn: () => riskApi.capitalAllocations().then((r) => r.data),
  });

  // Strategies
  const { data: strategies = [] } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list().then((r) => r.data),
  });

  // Risk Snapshot (for selected strategy)
  const { data: snapshot, isLoading: snapshotLoading } = useQuery({
    queryKey: ['risk-snapshot', selectedStrategy],
    queryFn: () => riskApi.snapshot(selectedStrategy).then((r) => r.data),
    enabled: !!selectedStrategy,
  });

  // Risk History (for selected strategy)
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['risk-history', selectedStrategy],
    queryFn: () => riskApi.history(selectedStrategy).then((r) => r.data),
    enabled: !!selectedStrategy,
  });

  // Mutations
  const activateKs = useMutation({
    mutationFn: (reason: string) => riskApi.activateKillSwitch(reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kill-switch'] });
      setShowTriggerConfirm(false);
      setTriggerReason('');
    },
  });

  const deactivateKs = useMutation({
    mutationFn: () => riskApi.deactivateKillSwitch(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kill-switch'] });
    },
  });

  const ksState = killSwitch?.state?.toUpperCase() ?? 'UNKNOWN';

  // Capital allocation chart data
  const allocationChartData = (capitalData?.allocations ?? []).map(
    (a: CapitalAllocation) => ({
      name: a.strategy_name,
      value: a.allocated_idr,
    }),
  );

  // Allocation table columns
  const allocationColumns = [
    {
      key: 'strategy_name',
      label: 'Strategy',
      render: (v: string) => (
        <span className="font-semibold text-slate-100">{v}</span>
      ),
    },
    {
      key: 'allocated_idr',
      label: 'Allocated',
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
    {
      key: 'target_weight_pct',
      label: 'Target',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => `${v.toFixed(2)}%`,
    },
    {
      key: 'nav_idr',
      label: 'NAV',
      align: 'right' as const,
      sortable: true,
      render: (v: number) => formatIdr(v),
    },
  ];

  // Risk history chart data
  const historyChartData = (historyData?.data_points ?? []).map(
    (d: RiskHistoryPoint) => ({
      date: format(new Date(d.timestamp), 'dd MMM'),
      var_1d_95: d.var_1d_95_idr,
      drawdown: d.drawdown_pct,
      daily_loss: d.daily_loss_pct,
    }),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Management"
        subtitle="Monitor risk metrics and manage kill switch"
      />

      {/* Kill Switch Section */}
      <div
        className={`rounded-xl border p-6 ${
          ksState === 'TRIGGERED'
            ? 'border-red-500/50 bg-red-500/5'
            : 'border-slate-700 bg-slate-800'
        }`}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-3">
            {ksState === 'ARMED' && <ShieldCheck className="h-6 w-6 text-emerald-400" />}
            {ksState === 'TRIGGERED' && (
              <ShieldAlert className="h-6 w-6 text-red-400" />
            )}
            {ksState === 'DISARMED' && (
              <ShieldOff className="h-6 w-6 text-amber-400" />
            )}
            Kill Switch
          </h3>
          <Badge variant={killSwitchBadgeVariant(ksState)}>{ksState}</Badge>
        </div>

        {ksLoading ? (
          <LoadingSpinner label="Loading kill switch status..." />
        ) : (
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
            {/* Large State Indicator */}
            <div className="flex items-center gap-4">
              <div
                className={`h-6 w-6 rounded-full ${killSwitchBg(ksState)}`}
              />
              <span
                className={`text-2xl font-bold ${killSwitchColor(ksState)}`}
              >
                {ksState}
              </span>
            </div>

            {/* Trigger Info */}
            {killSwitch && ksState === 'TRIGGERED' && (
              <div className="flex-1 space-y-1">
                {killSwitch.triggered_by && (
                  <p className="text-sm text-slate-400">
                    Triggered by:{' '}
                    <span className="text-slate-200 font-medium">
                      {killSwitch.triggered_by}
                    </span>
                  </p>
                )}
                {killSwitch.reason && (
                  <p className="text-sm text-red-400">
                    Reason: {killSwitch.reason}
                  </p>
                )}
                {killSwitch.triggered_at && (
                  <p className="text-xs text-slate-500">
                    At: {format(new Date(killSwitch.triggered_at), 'dd MMM yyyy HH:mm:ss')}
                  </p>
                )}
                {killSwitch.open_orders_cancelled > 0 && (
                  <p className="text-xs text-amber-400">
                    {killSwitch.open_orders_cancelled} open orders cancelled
                  </p>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center gap-3 ml-auto">
              {ksState !== 'TRIGGERED' && (
                <>
                  {!showTriggerConfirm ? (
                    <button
                      onClick={() => setShowTriggerConfirm(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-lg transition-colors"
                    >
                      <AlertTriangle className="h-4 w-4" />
                      Trigger Kill Switch
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={triggerReason}
                        onChange={(e) => setTriggerReason(e.target.value)}
                        placeholder="Reason for triggering..."
                        className="px-3 py-2 bg-slate-900/50 border border-red-500/30 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-red-500/40 w-64"
                      />
                      <button
                        onClick={() => activateKs.mutate(triggerReason || 'Manual trigger')}
                        disabled={activateKs.isPending}
                        className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white text-sm font-semibold rounded-lg transition-colors"
                      >
                        {activateKs.isPending ? (
                          <LoadingSpinner size="sm" />
                        ) : (
                          'Confirm'
                        )}
                      </button>
                      <button
                        onClick={() => {
                          setShowTriggerConfirm(false);
                          setTriggerReason('');
                        }}
                        className="px-3 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </>
              )}
              {ksState === 'TRIGGERED' && (
                <button
                  onClick={() => deactivateKs.mutate()}
                  disabled={deactivateKs.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white text-sm font-semibold rounded-lg transition-colors"
                >
                  {deactivateKs.isPending ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  Reset Kill Switch
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Capital Allocations Section */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <h3 className="text-base font-semibold text-slate-100 mb-4 flex items-center gap-2">
          <Wallet className="h-5 w-5 text-slate-400" />
          Capital Allocations
        </h3>

        {capitalLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner label="Loading allocations..." />
          </div>
        ) : (
          <>
            {/* Summary Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <StatCard
                title="Total Capital"
                value={formatIdr(capitalData?.total_capital_idr ?? 0)}
                icon={Wallet}
              />
              <StatCard
                title="Allocated"
                value={formatIdr(capitalData?.total_allocated_idr ?? 0)}
                icon={Target}
              />
              <StatCard
                title="Unallocated"
                value={formatIdr(capitalData?.total_unallocated_idr ?? 0)}
                icon={Activity}
              />
            </div>

            {/* Chart + Table */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Pie Chart */}
              <div className="flex items-center justify-center">
                {allocationChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={allocationChartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        innerRadius={50}
                        paddingAngle={2}
                        label={((props: any) =>
                          `${props.name || ''} ${((props.percent ?? 0) * 100).toFixed(0)}%`
                        ) as any}
                        labelLine={false}
                      >
                        {allocationChartData.map((_: unknown, idx: number) => (
                          <Cell
                            key={idx}
                            fill={PIE_COLORS[idx % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1e293b',
                          border: '1px solid #475569',
                          borderRadius: '0.5rem',
                          color: '#f1f5f9',
                          fontSize: 12,
                        }}
                        formatter={((value: any) => [formatIdr(value), 'Allocated']) as any}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-slate-500">No allocations.</p>
                )}
              </div>

              {/* Table */}
              <div className="lg:col-span-2">
                <DataTable
                  columns={allocationColumns}
                  data={capitalData?.allocations ?? []}
                  emptyMessage="No capital allocations"
                />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Risk Snapshot Section */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <Activity className="h-5 w-5 text-slate-400" />
            Risk Snapshot
          </h3>
          <select
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
            className="px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40 min-w-48"
          >
            <option value="">Select strategy...</option>
            {strategies.map((s: Strategy) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {!selectedStrategy ? (
          <p className="text-sm text-slate-500 text-center py-12">
            Select a strategy to view risk metrics.
          </p>
        ) : snapshotLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner label="Loading risk snapshot..." />
          </div>
        ) : snapshot ? (
          <div className="space-y-6">
            {/* Top-level metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  NAV
                </p>
                <p className="text-lg font-bold text-slate-100">
                  {formatIdr(snapshot.nav_idr)}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Gross Exposure
                </p>
                <p className="text-lg font-bold text-slate-100">
                  {formatIdr(snapshot.exposure.gross_exposure_idr)}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Net Exposure
                </p>
                <p className="text-lg font-bold text-slate-100">
                  {formatIdr(snapshot.exposure.net_exposure_idr)}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Beta vs IHSG
                </p>
                <p className="text-lg font-bold text-slate-100">
                  {snapshot.exposure.beta_vs_ihsg.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Concentration */}
            <div>
              <h4 className="text-sm font-semibold text-slate-300 mb-3">
                Concentration Metrics
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Sector HHI
                  </p>
                  <p className="text-lg font-bold text-slate-100">
                    {(snapshot.concentration.sector_hhi * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Top 5 Weight
                  </p>
                  <p className="text-lg font-bold text-slate-100">
                    {snapshot.concentration.top5_weight_pct.toFixed(1)}%
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Largest Position
                  </p>
                  <p className="text-lg font-bold text-slate-100">
                    {snapshot.concentration.largest_position_pct.toFixed(1)}%
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {snapshot.concentration.largest_position_symbol}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    Positions
                  </p>
                  <p className="text-lg font-bold text-slate-100">
                    {snapshot.concentration.num_positions}
                  </p>
                </div>
              </div>
            </div>

            {/* VaR Metrics */}
            <div>
              <h4 className="text-sm font-semibold text-slate-300 mb-3">
                Value at Risk
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    1D VaR (95%)
                  </p>
                  <p className="text-lg font-bold text-red-400">
                    {formatIdr(snapshot.var.var_1d_95_idr)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    5D VaR (95%)
                  </p>
                  <p className="text-lg font-bold text-red-400">
                    {formatIdr(snapshot.var.var_5d_95_idr)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    1D VaR (99%)
                  </p>
                  <p className="text-lg font-bold text-red-400">
                    {formatIdr(snapshot.var.var_1d_99_idr)}
                  </p>
                </div>
              </div>
            </div>

            {/* Drawdown and Daily Loss */}
            <div className="grid grid-cols-2 gap-4">
              <div
                className={`p-4 rounded-lg border ${
                  snapshot.drawdown_pct > 5
                    ? 'bg-red-500/5 border-red-500/30'
                    : 'bg-slate-900/50 border-slate-700/50'
                }`}
              >
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
                  <TrendingDown className="h-3.5 w-3.5" />
                  Drawdown
                </p>
                <p
                  className={`text-2xl font-bold ${
                    snapshot.drawdown_pct > 5 ? 'text-red-400' : 'text-amber-400'
                  }`}
                >
                  {snapshot.drawdown_pct.toFixed(2)}%
                </p>
              </div>
              <div
                className={`p-4 rounded-lg border ${
                  snapshot.daily_loss_pct > 2
                    ? 'bg-red-500/5 border-red-500/30'
                    : 'bg-slate-900/50 border-slate-700/50'
                }`}
              >
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Daily Loss
                </p>
                <p
                  className={`text-2xl font-bold ${
                    snapshot.daily_loss_pct > 2 ? 'text-red-400' : 'text-amber-400'
                  }`}
                >
                  {snapshot.daily_loss_pct.toFixed(2)}%
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500 text-center py-12">
            No risk snapshot available for this strategy.
          </p>
        )}
      </div>

      {/* Risk History Chart */}
      {selectedStrategy && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">
            Risk History
          </h3>
          {historyLoading ? (
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner label="Loading risk history..." />
            </div>
          ) : historyChartData.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-12">
              No risk history data available.
            </p>
          ) : (
            <div className="space-y-6">
              {/* VaR over time */}
              <div>
                <h4 className="text-sm font-semibold text-slate-300 mb-3">
                  1D VaR (95%) Over Time
                </h4>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart
                    data={historyChartData}
                    margin={{ top: 5, right: 10, left: 10, bottom: 0 }}
                  >
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
                      formatter={((value: any) => [formatIdr(value), 'VaR 1D 95%']) as any}
                    />
                    <Line
                      type="monotone"
                      dataKey="var_1d_95"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Drawdown over time */}
              <div>
                <h4 className="text-sm font-semibold text-slate-300 mb-3">
                  Drawdown Over Time
                </h4>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart
                    data={historyChartData}
                    margin={{ top: 5, right: 10, left: 10, bottom: 0 }}
                  >
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
                      tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #475569',
                        borderRadius: '0.5rem',
                        color: '#f1f5f9',
                        fontSize: 13,
                      }}
                      formatter={((value: any) => [`${value.toFixed(2)}%`, 'Drawdown']) as any}
                    />
                    <Line
                      type="monotone"
                      dataKey="drawdown"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
