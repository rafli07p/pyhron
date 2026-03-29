import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Plus,
  Pencil,
  Trash2,
  Power,
  X,
  Zap,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { strategyApi } from '../../api/endpoints';
import type { Strategy } from '../../types';

const STRATEGY_TYPES = [
  'mean_reversion',
  'momentum',
  'pairs_trading',
  'statistical_arbitrage',
  'trend_following',
  'market_making',
  'value',
] as const;

function strategyTypeBadgeVariant(type: string): 'success' | 'danger' | 'warning' | 'info' | 'neutral' {
  switch (type) {
    case 'momentum':
    case 'trend_following':
      return 'success';
    case 'mean_reversion':
    case 'statistical_arbitrage':
      return 'info';
    case 'pairs_trading':
      return 'warning';
    case 'market_making':
      return 'danger';
    default:
      return 'neutral';
  }
}

function formatPct(value: number | undefined | null): string {
  if (value == null) return '--';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatNumber(value: number | undefined | null): string {
  if (value == null) return '--';
  return value.toLocaleString('id-ID');
}

function formatRatio(value: number | undefined | null): string {
  if (value == null) return '--';
  return value.toFixed(2);
}

interface StrategyFormData {
  name: string;
  strategy_type: string;
  description: string;
  parameters: string;
  risk_limits: string;
}

const emptyForm: StrategyFormData = {
  name: '',
  strategy_type: 'momentum',
  description: '',
  parameters: '{}',
  risk_limits: '{}',
};

function StrategyFormModal({
  isOpen,
  onClose,
  initialData,
  editingId,
}: {
  isOpen: boolean;
  onClose: () => void;
  initialData: StrategyFormData;
  editingId: string | null;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<StrategyFormData>(initialData);
  const [jsonError, setJsonError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: { name: string; strategy_type: string; description?: string; parameters?: Record<string, unknown>; risk_limits?: Record<string, unknown> }) =>
      strategyApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string; parameters?: Record<string, unknown>; risk_limits?: Record<string, unknown> } }) =>
      strategyApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      onClose();
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setJsonError(null);

    let parameters: Record<string, unknown>;
    let risk_limits: Record<string, unknown>;
    try {
      parameters = JSON.parse(form.parameters);
    } catch {
      setJsonError('Invalid JSON in Parameters field');
      return;
    }
    try {
      risk_limits = JSON.parse(form.risk_limits);
    } catch {
      setJsonError('Invalid JSON in Risk Limits field');
      return;
    }

    if (editingId) {
      updateMutation.mutate({
        id: editingId,
        data: {
          name: form.name,
          description: form.description,
          parameters,
          risk_limits,
        },
      });
    } else {
      createMutation.mutate({
        name: form.name,
        strategy_type: form.strategy_type,
        description: form.description || undefined,
        parameters,
        risk_limits,
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-slate-100">
            {editingId ? 'Edit Strategy' : 'New Strategy'}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Name
            </label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="My Strategy"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Strategy Type
            </label>
            <select
              value={form.strategy_type}
              onChange={(e) => setForm({ ...form, strategy_type: e.target.value })}
              disabled={!!editingId}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            >
              {STRATEGY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              placeholder="Strategy description..."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Parameters (JSON)
            </label>
            <textarea
              value={form.parameters}
              onChange={(e) => setForm({ ...form, parameters: e.target.value })}
              rows={4}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 font-mono placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              placeholder='{"lookback_days": 20, "threshold": 0.05}'
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Risk Limits (JSON)
            </label>
            <textarea
              value={form.risk_limits}
              onChange={(e) => setForm({ ...form, risk_limits: e.target.value })}
              rows={4}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 font-mono placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              placeholder='{"max_position_pct": 10, "max_drawdown_pct": 15}'
            />
          </div>

          {jsonError && (
            <p className="text-sm text-red-400">{jsonError}</p>
          )}
          {(createMutation.isError || updateMutation.isError) && (
            <p className="text-sm text-red-400">
              {(createMutation.error || updateMutation.error)?.message ?? 'An error occurred'}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {isSubmitting && <LoadingSpinner size="sm" />}
              {editingId ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StrategyDetailModal({
  strategy,
  onClose,
}: {
  strategy: Strategy;
  onClose: () => void;
}) {
  const { data: performance, isLoading: perfLoading } = useQuery({
    queryKey: ['strategy-performance', strategy.id],
    queryFn: () => strategyApi.performance(strategy.id).then((r) => r.data),
  });

  const chartData = performance
    ? [
        { name: 'Return', value: performance.total_return_pct },
        { name: 'Sharpe', value: performance.sharpe_ratio },
        { name: 'Win Rate', value: performance.win_rate },
        { name: 'Drawdown', value: Math.abs(performance.max_drawdown_pct) },
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-lg font-bold text-slate-100">{strategy.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={strategyTypeBadgeVariant(strategy.strategy_type)}>
                {strategy.strategy_type.replace(/_/g, ' ')}
              </Badge>
              <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${strategy.is_enabled ? 'text-emerald-400' : 'text-slate-500'}`}>
                <span className={`h-2 w-2 rounded-full ${strategy.is_enabled ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                {strategy.is_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {strategy.description && (
          <p className="text-sm text-slate-400 mb-5">{strategy.description}</p>
        )}

        {/* Parameters */}
        <div className="mb-5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
            Parameters
          </h4>
          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3">
            {Object.keys(strategy.parameters).length === 0 ? (
              <p className="text-sm text-slate-500">No parameters configured</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(strategy.parameters).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-2 px-2 py-1.5 rounded bg-slate-800/60">
                    <span className="text-xs font-mono text-slate-400">{key}</span>
                    <span className="text-xs font-semibold text-slate-200">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Risk Limits */}
        <div className="mb-5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
            Risk Limits
          </h4>
          <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3">
            {Object.keys(strategy.risk_limits).length === 0 ? (
              <p className="text-sm text-slate-500">No risk limits configured</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(strategy.risk_limits).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-2 px-2 py-1.5 rounded bg-slate-800/60">
                    <span className="text-xs font-mono text-slate-400">{key}</span>
                    <span className="text-xs font-semibold text-slate-200">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Performance */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
            Performance
          </h4>
          {perfLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner label="Loading performance..." />
            </div>
          ) : performance ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">Total Return</p>
                  <p className={`text-lg font-bold ${performance.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatPct(performance.total_return_pct)}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">Sharpe Ratio</p>
                  <p className="text-lg font-bold text-slate-100">{formatRatio(performance.sharpe_ratio)}</p>
                </div>
                <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">Max Drawdown</p>
                  <p className="text-lg font-bold text-red-400">{formatPct(performance.max_drawdown_pct)}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">Win Rate</p>
                  <p className="text-lg font-bold text-slate-100">{formatPct(performance.win_rate)}</p>
                </div>
                <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">Total Trades</p>
                  <p className="text-lg font-bold text-slate-100">{formatNumber(performance.total_trades)}</p>
                </div>
                <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">Avg Holding</p>
                  <p className="text-lg font-bold text-slate-100">{formatRatio(performance.avg_holding_period_days)}d</p>
                </div>
              </div>

              {/* Bar Chart */}
              <div className="rounded-lg bg-slate-900/60 border border-slate-700/50 p-4">
                <ResponsiveContainer width="100%" height={200}>
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
                    <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-4 text-center">No performance data available</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function StrategiesPage() {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [enabledOnly, setEnabledOnly] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);
  const [detailStrategy, setDetailStrategy] = useState<Strategy | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const { data: strategies, isLoading } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list().then((r) => r.data),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enable }: { id: string; enable: boolean }) =>
      strategyApi.update(id, { is_enabled: enable }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => strategyApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      setDeleteConfirm(null);
    },
  });

  const filtered = (strategies ?? []).filter((s) => {
    if (typeFilter && s.strategy_type !== typeFilter) return false;
    if (enabledOnly && !s.is_enabled) return false;
    return true;
  });

  const openEdit = (strategy: Strategy) => {
    setEditingStrategy(strategy);
    setFormOpen(true);
  };

  const openCreate = () => {
    setEditingStrategy(null);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingStrategy(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner label="Loading strategies..." size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Strategy Management" subtitle="Configure and monitor trading strategies">
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-500 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Strategy
        </button>
      </PageHeader>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            {STRATEGY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <div
            onClick={() => setEnabledOnly(!enabledOnly)}
            className={`relative w-9 h-5 rounded-full transition-colors ${
              enabledOnly ? 'bg-blue-600' : 'bg-slate-600'
            }`}
          >
            <div
              className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                enabledOnly ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </div>
          <span className="text-sm text-slate-400">Enabled only</span>
        </label>

        <span className="text-xs text-slate-500 ml-auto">
          {filtered.length} {filtered.length === 1 ? 'strategy' : 'strategies'}
        </span>
      </div>

      {/* Strategy Cards Grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <Zap className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No strategies found. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              onView={() => setDetailStrategy(strategy)}
              onEdit={() => openEdit(strategy)}
              onToggle={() =>
                toggleMutation.mutate({ id: strategy.id, enable: !strategy.is_enabled })
              }
              onDelete={() => setDeleteConfirm(strategy.id)}
              isToggling={toggleMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl mx-4">
            <h3 className="text-lg font-bold text-slate-100 mb-2">Delete Strategy</h3>
            <p className="text-sm text-slate-400 mb-5">
              Are you sure you want to delete this strategy? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors flex items-center gap-2"
              >
                {deleteMutation.isPending && <LoadingSpinner size="sm" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Form Modal */}
      <StrategyFormModal
        isOpen={formOpen}
        onClose={closeForm}
        initialData={
          editingStrategy
            ? {
                name: editingStrategy.name,
                strategy_type: editingStrategy.strategy_type,
                description: editingStrategy.description,
                parameters: JSON.stringify(editingStrategy.parameters, null, 2),
                risk_limits: JSON.stringify(editingStrategy.risk_limits, null, 2),
              }
            : emptyForm
        }
        editingId={editingStrategy?.id ?? null}
      />

      {/* Detail Modal */}
      {detailStrategy && (
        <StrategyDetailModal
          strategy={detailStrategy}
          onClose={() => setDetailStrategy(null)}
        />
      )}
    </div>
  );
}

function StrategyCard({
  strategy,
  onView,
  onEdit,
  onToggle,
  onDelete,
  isToggling,
}: {
  strategy: Strategy;
  onView: () => void;
  onEdit: () => void;
  onToggle: () => void;
  onDelete: () => void;
  isToggling: boolean;
}) {
  const { data: performance } = useQuery({
    queryKey: ['strategy-performance', strategy.id],
    queryFn: () => strategyApi.performance(strategy.id).then((r) => r.data),
    staleTime: 60_000,
  });

  return (
    <div
      className="rounded-xl border border-slate-700 bg-slate-800 p-5 hover:border-slate-600 transition-colors cursor-pointer"
      onClick={onView}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-bold text-slate-100 truncate">{strategy.name}</h3>
          <div className="flex items-center gap-2 mt-1.5">
            <Badge variant={strategyTypeBadgeVariant(strategy.strategy_type)}>
              {strategy.strategy_type.replace(/_/g, ' ')}
            </Badge>
            <span className={`inline-flex items-center gap-1 text-xs font-medium ${strategy.is_enabled ? 'text-emerald-400' : 'text-slate-500'}`}>
              <span className={`h-2 w-2 rounded-full ${strategy.is_enabled ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              {strategy.is_enabled ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </div>

      {strategy.description && (
        <p className="text-xs text-slate-400 mb-4 line-clamp-2">{strategy.description}</p>
      )}

      {/* Performance Summary */}
      {performance ? (
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="rounded-lg bg-slate-900/60 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Return</p>
            <p className={`text-sm font-bold ${performance.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {formatPct(performance.total_return_pct)}
            </p>
          </div>
          <div className="rounded-lg bg-slate-900/60 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Sharpe</p>
            <p className="text-sm font-bold text-slate-200">{formatRatio(performance.sharpe_ratio)}</p>
          </div>
          <div className="rounded-lg bg-slate-900/60 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Drawdown</p>
            <p className="text-sm font-bold text-red-400">{formatPct(performance.max_drawdown_pct)}</p>
          </div>
          <div className="rounded-lg bg-slate-900/60 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Win Rate</p>
            <p className="text-sm font-bold text-slate-200">{formatPct(performance.win_rate)}</p>
          </div>
          <div className="rounded-lg bg-slate-900/60 p-2 text-center col-span-2">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Trades</p>
            <p className="text-sm font-bold text-slate-200">{formatNumber(performance.total_trades)}</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2 mb-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={`rounded-lg bg-slate-900/60 p-2 text-center ${i === 4 ? 'col-span-2' : ''}`}>
              <div className="h-3 w-12 mx-auto rounded bg-slate-700/50 mb-1" />
              <div className="h-4 w-8 mx-auto rounded bg-slate-700/50" />
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 border-t border-slate-700/50 pt-3" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onToggle}
          disabled={isToggling}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            strategy.is_enabled
              ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              : 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30'
          }`}
          title={strategy.is_enabled ? 'Disable' : 'Enable'}
        >
          <Power className="h-3.5 w-3.5" />
          {strategy.is_enabled ? 'Disable' : 'Enable'}
        </button>
        <button
          onClick={onEdit}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
          title="Edit"
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </button>
        <button
          onClick={onDelete}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors ml-auto"
          title="Delete"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
