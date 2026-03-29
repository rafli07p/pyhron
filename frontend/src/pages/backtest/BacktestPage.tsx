import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  Play,
  X,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FlaskConical,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  BarChart3,
  Calendar,
  DollarSign,
  Gauge,
} from 'lucide-react';
import { format } from 'date-fns';

import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import DataTable from '../../components/common/DataTable';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import type { Column } from '../../components/common/DataTable';
import { backtestApi } from '../../api/endpoints';
import type {
  BacktestRequest,
  BacktestResult,
  BacktestMetrics,
} from '../../types';

const STRATEGY_TYPES = [
  'mean_reversion',
  'momentum',
  'pairs_trading',
  'statistical_arbitrage',
  'trend_following',
  'market_making',
  'value',
] as const;

function formatIDR(value: number): string {
  if (value >= 1_000_000_000_000) return `Rp ${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (value >= 1_000_000_000) return `Rp ${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `Rp ${(value / 1_000_000).toFixed(2)}M`;
  return `Rp ${value.toLocaleString('id-ID')}`;
}

function formatPct(value: number | undefined | null): string {
  if (value == null) return '--';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatRatio(value: number | undefined | null): string {
  if (value == null) return '--';
  return value.toFixed(2);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  try {
    return format(new Date(dateStr), 'dd MMM yyyy');
  } catch {
    return dateStr;
  }
}

function statusBadgeVariant(status: string): 'success' | 'danger' | 'warning' | 'info' | 'neutral' {
  switch (status) {
    case 'completed':
      return 'success';
    case 'running':
      return 'warning';
    case 'submitted':
    case 'pending':
      return 'info';
    case 'failed':
      return 'danger';
    default:
      return 'neutral';
  }
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
    case 'running':
      return <Loader2 className="h-5 w-5 text-amber-400 animate-spin" />;
    case 'submitted':
    case 'pending':
      return <Clock className="h-5 w-5 text-blue-400" />;
    case 'failed':
      return <AlertCircle className="h-5 w-5 text-red-400" />;
    default:
      return <Clock className="h-5 w-5 text-slate-400" />;
  }
}

function SymbolChips({
  symbols,
  onRemove,
}: {
  symbols: string[];
  onRemove: (sym: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-1.5">
      {symbols.map((sym) => (
        <span
          key={sym}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30"
        >
          {sym}
          <button
            type="button"
            onClick={() => onRemove(sym)}
            className="hover:text-blue-200 transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  colorClass,
  icon: Icon,
}: {
  label: string;
  value: string;
  colorClass?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3">
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon className="h-3.5 w-3.5 text-slate-500" />}
        <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      </div>
      <p className={`text-lg font-bold ${colorClass ?? 'text-slate-100'}`}>{value}</p>
    </div>
  );
}

function BacktestConfigForm({ onSubmitted }: { onSubmitted: (taskId: string) => void }) {
  const queryClient = useQueryClient();
  const [strategyType, setStrategyType] = useState<string>('momentum');
  const [symbolInput, setSymbolInput] = useState('');
  const [symbols, setSymbols] = useState<string[]>([]);
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2025-01-01');
  const [initialCapital, setInitialCapital] = useState(1_000_000_000);
  const [slippageBps, setSlippageBps] = useState(5);
  const [strategyParams, setStrategyParams] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);

  const submitMutation = useMutation({
    mutationFn: (data: BacktestRequest) => backtestApi.submit(data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
      onSubmitted(res.data.task_id);
    },
  });

  const addSymbols = useCallback(() => {
    if (!symbolInput.trim()) return;
    const newSymbols = symbolInput
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter((s) => s.length > 0 && !symbols.includes(s));
    setSymbols((prev) => [...prev, ...newSymbols]);
    setSymbolInput('');
  }, [symbolInput, symbols]);

  const removeSymbol = (sym: string) => {
    setSymbols((prev) => prev.filter((s) => s !== sym));
  };

  const handleSymbolKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addSymbols();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setJsonError(null);

    if (symbols.length === 0) return;

    let parsedParams: Record<string, unknown> | undefined;
    if (strategyParams.trim()) {
      try {
        parsedParams = JSON.parse(strategyParams);
      } catch {
        setJsonError('Invalid JSON in strategy parameters');
        return;
      }
    }

    submitMutation.mutate({
      strategy_type: strategyType,
      symbols,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      slippage_bps: slippageBps,
      strategy_params: parsedParams,
    });
  };

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
      <h3 className="text-base font-semibold text-slate-100 mb-4 flex items-center gap-2">
        <FlaskConical className="h-5 w-5 text-blue-400" />
        Backtest Configuration
      </h3>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Strategy Type */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Strategy Type
            </label>
            <select
              value={strategyType}
              onChange={(e) => setStrategyType(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {STRATEGY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {/* Symbols */}
          <div className="lg:col-span-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Symbols
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={symbolInput}
                onChange={(e) => setSymbolInput(e.target.value)}
                onKeyDown={handleSymbolKeyDown}
                onBlur={addSymbols}
                placeholder="BBCA, BBRI, TLKM..."
                className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={addSymbols}
                className="px-3 py-2 rounded-lg text-sm font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
              >
                Add
              </button>
            </div>
            {symbols.length > 0 && (
              <SymbolChips symbols={symbols} onRemove={removeSymbol} />
            )}
          </div>

          {/* Start Date */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* End Date */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Initial Capital */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Initial Capital (IDR)
            </label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              min={0}
              step={1_000_000}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="text-[10px] text-slate-500 mt-1">{formatIDR(initialCapital)}</p>
          </div>

          {/* Slippage */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Slippage (bps)
            </label>
            <input
              type="number"
              value={slippageBps}
              onChange={(e) => setSlippageBps(Number(e.target.value))}
              min={0}
              max={100}
              step={1}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Strategy Params */}
          <div className="md:col-span-2 lg:col-span-1">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Strategy Params (JSON, optional)
            </label>
            <textarea
              value={strategyParams}
              onChange={(e) => setStrategyParams(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 font-mono placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              placeholder='{"lookback": 20}'
            />
          </div>
        </div>

        {jsonError && <p className="text-sm text-red-400 mt-2">{jsonError}</p>}
        {submitMutation.isError && (
          <p className="text-sm text-red-400 mt-2">
            {submitMutation.error?.message ?? 'Failed to submit backtest'}
          </p>
        )}

        <div className="flex items-center justify-between mt-5">
          <p className="text-xs text-slate-500">
            {symbols.length === 0
              ? 'Add at least one symbol to run a backtest'
              : `${symbols.length} symbol${symbols.length > 1 ? 's' : ''} selected`}
          </p>
          <button
            type="submit"
            disabled={submitMutation.isPending || symbols.length === 0}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {submitMutation.isPending ? (
              <LoadingSpinner size="sm" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Run Backtest
          </button>
        </div>
      </form>
    </div>
  );
}

function MetricsDashboard({ metrics }: { metrics: BacktestMetrics }) {
  const returnColor = metrics.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400';

  const chartData = [
    { name: 'Return', value: metrics.total_return_pct, color: metrics.total_return_pct >= 0 ? '#34d399' : '#f87171' },
    { name: 'CAGR', value: metrics.cagr_pct, color: metrics.cagr_pct >= 0 ? '#34d399' : '#f87171' },
    { name: 'Sharpe', value: metrics.sharpe_ratio, color: '#3b82f6' },
    { name: 'Sortino', value: metrics.sortino_ratio, color: '#3b82f6' },
    { name: 'Calmar', value: metrics.calmar_ratio, color: '#3b82f6' },
    { name: 'Win Rate', value: metrics.win_rate_pct, color: '#3b82f6' },
    { name: 'Profit Factor', value: metrics.profit_factor, color: '#a78bfa' },
  ];

  return (
    <div className="space-y-4">
      {/* Row 1: Return metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Total Return"
          value={formatPct(metrics.total_return_pct)}
          colorClass={returnColor}
          icon={TrendingUp}
        />
        <MetricCard
          label="CAGR"
          value={formatPct(metrics.cagr_pct)}
          colorClass={metrics.cagr_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
          icon={TrendingUp}
        />
        <MetricCard
          label="Sharpe Ratio"
          value={formatRatio(metrics.sharpe_ratio)}
          icon={BarChart3}
        />
        <MetricCard
          label="Sortino Ratio"
          value={formatRatio(metrics.sortino_ratio)}
          icon={BarChart3}
        />
        <MetricCard
          label="Calmar Ratio"
          value={formatRatio(metrics.calmar_ratio)}
          icon={BarChart3}
        />
      </div>

      {/* Row 2: Risk metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Max Drawdown"
          value={formatPct(metrics.max_drawdown_pct)}
          colorClass="text-red-400"
          icon={TrendingDown}
        />
        <MetricCard
          label="DD Duration"
          value={`${metrics.max_drawdown_duration_days}d`}
          icon={Calendar}
        />
        <MetricCard
          label="Win Rate"
          value={formatPct(metrics.win_rate_pct)}
          colorClass="text-blue-400"
          icon={Target}
        />
        <MetricCard
          label="Profit Factor"
          value={formatRatio(metrics.profit_factor)}
          icon={Gauge}
        />
        <MetricCard
          label="Omega Ratio"
          value={formatRatio(metrics.omega_ratio)}
          icon={Activity}
        />
      </div>

      {/* Row 3: Trade metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Total Trades"
          value={metrics.total_trades.toLocaleString('id-ID')}
          icon={Activity}
        />
        <MetricCard
          label="Cost Drag (Ann.)"
          value={formatPct(metrics.cost_drag_annualized_pct)}
          colorClass="text-amber-400"
          icon={DollarSign}
        />
      </div>

      {/* Bar Chart Comparison */}
      <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
          Key Metrics Comparison
        </h4>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="name"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '0.5rem',
                color: '#f1f5f9',
                fontSize: 13,
              }}
              formatter={(value: any) => [Number(value).toFixed(2), 'Value']}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, idx) => (
                <Cell key={idx} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function BacktestDetailPanel({ taskId }: { taskId: string }) {
  const { data: result, isLoading: resultLoading } = useQuery({
    queryKey: ['backtest', taskId],
    queryFn: () => backtestApi.get(taskId).then((r) => r.data),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'running' || status === 'submitted' || status === 'pending') return 5000;
      return false;
    },
  });

  const isCompleted = result?.status === 'completed';

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['backtest-metrics', taskId],
    queryFn: () => backtestApi.metrics(taskId).then((r) => r.data),
    enabled: isCompleted,
  });

  if (resultLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner label="Loading backtest details..." />
      </div>
    );
  }

  if (!result) {
    return <p className="text-sm text-slate-500 py-8 text-center">Backtest not found</p>;
  }

  return (
    <div className="space-y-4">
      {/* Status Card */}
      <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-4">
        <div className="flex items-center gap-3">
          <StatusIcon status={result.status} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-slate-100">{result.strategy_name}</h4>
              <Badge variant={statusBadgeVariant(result.status)}>
                {result.status}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {result.symbols.join(', ')} | {formatDate(result.start_date)} - {formatDate(result.end_date)}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-slate-500">Capital</p>
            <p className="text-sm font-semibold text-slate-200">{formatIDR(result.initial_capital)}</p>
            {result.final_capital > 0 && result.status === 'completed' && (
              <p className={`text-xs font-medium ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-400'}`}>
                {formatIDR(result.final_capital)}
              </p>
            )}
          </div>
        </div>

        {(result.status === 'running' || result.status === 'submitted' || result.status === 'pending') && (
          <div className="mt-3">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 animate-pulse"
                  style={{ width: result.status === 'running' ? '60%' : '10%' }}
                />
              </div>
              <span className="text-xs text-slate-500">
                {result.status === 'running' ? 'Processing...' : 'Queued'}
              </span>
            </div>
          </div>
        )}

        {result.status === 'failed' && result.error_message && (
          <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400">{result.error_message}</p>
          </div>
        )}
      </div>

      {/* Metrics Dashboard */}
      {isCompleted && metricsLoading && (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner label="Loading metrics..." />
        </div>
      )}
      {isCompleted && metrics && <MetricsDashboard metrics={metrics} />}
    </div>
  );
}

export default function BacktestPage() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const hasRunningBacktests = (data: BacktestResult[] | undefined) => {
    return data?.some(
      (b) => b.status === 'running' || b.status === 'submitted' || b.status === 'pending'
    );
  };

  const { data: backtests, isLoading: historyLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestApi.list().then((r) => r.data),
    refetchInterval: (query) => {
      if (hasRunningBacktests(query.state.data)) return 5000;
      return false;
    },
  });

  const historyColumns: Column[] = [
    {
      key: 'task_id',
      label: 'Task ID',
      render: (val: string) => (
        <span className="font-mono text-xs">{val?.slice(0, 8)}...</span>
      ),
    },
    {
      key: 'strategy_name',
      label: 'Strategy',
      sortable: true,
    },
    {
      key: 'symbols',
      label: 'Symbols',
      render: (val: string[]) => (
        <span className="text-xs">{val?.join(', ')}</span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (val: string) => (
        <Badge variant={statusBadgeVariant(val)}>{val}</Badge>
      ),
    },
    {
      key: 'start_date',
      label: 'Start',
      sortable: true,
      render: (val: string) => <span className="text-xs">{formatDate(val)}</span>,
    },
    {
      key: 'end_date',
      label: 'End',
      sortable: true,
      render: (val: string) => <span className="text-xs">{formatDate(val)}</span>,
    },
    {
      key: 'initial_capital',
      label: 'Initial Capital',
      align: 'right' as const,
      sortable: true,
      render: (val: number) => <span className="text-xs">{formatIDR(val)}</span>,
    },
    {
      key: 'final_capital',
      label: 'Final Capital',
      align: 'right' as const,
      sortable: true,
      render: (val: number, row: BacktestResult) => {
        if (!val || row.status !== 'completed') return <span className="text-xs text-slate-500">--</span>;
        const isGain = val >= row.initial_capital;
        return (
          <span className={`text-xs font-medium ${isGain ? 'text-emerald-400' : 'text-red-400'}`}>
            {formatIDR(val)}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtesting Engine"
        subtitle="Test strategies against historical data"
      />

      {/* Configuration Form */}
      <BacktestConfigForm onSubmitted={(taskId) => setSelectedTaskId(taskId)} />

      {/* Backtest History */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <h3 className="text-base font-semibold text-slate-100 mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5 text-slate-400" />
          Backtest History
        </h3>
        <DataTable
          columns={historyColumns}
          data={backtests ?? []}
          loading={historyLoading}
          emptyMessage="No backtests yet. Configure and run one above."
          onRowClick={(row: BacktestResult) => setSelectedTaskId(row.task_id)}
        />
      </div>

      {/* Selected Backtest Detail */}
      {selectedTaskId && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-blue-400" />
              Backtest Results
            </h3>
            <button
              onClick={() => setSelectedTaskId(null)}
              className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <BacktestDetailPanel taskId={selectedTaskId} />
        </div>
      )}
    </div>
  );
}
