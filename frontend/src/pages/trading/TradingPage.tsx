import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Send,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import DataTable from '../../components/common/DataTable';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { tradingApi, strategyApi } from '../../api/endpoints';
import type {
  OrderSubmitRequest,
  PnLResponse,
  CircuitBreakerStatus,
  Strategy,
} from '../../types';

function formatIdr(value: number): string {
  if (Math.abs(value) >= 1_000_000_000_000) return `Rp ${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (Math.abs(value) >= 1_000_000_000) return `Rp ${(value / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(value) >= 1_000_000) return `Rp ${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `Rp ${(value / 1_000).toFixed(1)}K`;
  return `Rp ${value.toFixed(0)}`;
}

function statusBadgeVariant(status: string): 'success' | 'danger' | 'warning' | 'info' | 'neutral' {
  switch (status.toUpperCase()) {
    case 'FILLED': return 'success';
    case 'CANCELLED': case 'REJECTED': return 'danger';
    case 'PARTIALLY_FILLED': return 'warning';
    case 'PENDING': case 'NEW': return 'info';
    default: return 'neutral';
  }
}

const ORDER_STATUSES = ['ALL', 'NEW', 'PENDING', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED'];

export default function TradingPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Order form state
  const [symbol, setSymbol] = useState('');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [quantity, setQuantity] = useState('');
  const [limitPrice, setLimitPrice] = useState('');
  const [strategyId, setStrategyId] = useState('');

  // Queries
  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ['orders', statusFilter],
    queryFn: () =>
      tradingApi
        .getOrders(statusFilter === 'ALL' ? {} : { status: statusFilter })
        .then((r) => r.data),
    refetchInterval: 5000,
  });

  const { data: pnlData = [], isLoading: pnlLoading } = useQuery({
    queryKey: ['trading-pnl'],
    queryFn: () => tradingApi.pnl().then((r) => r.data),
  });

  const { data: circuitBreakers = [], isLoading: cbLoading } = useQuery({
    queryKey: ['circuit-breakers'],
    queryFn: () => tradingApi.circuitBreakers().then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list().then((r) => r.data),
  });

  // Mutations
  const submitOrder = useMutation({
    mutationFn: (data: OrderSubmitRequest) => tradingApi.submitOrder(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setSymbol('');
      setQuantity('');
      setLimitPrice('');
    },
  });

  const resetCb = useMutation({
    mutationFn: (strategyId: string) => tradingApi.resetCircuitBreaker(strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['circuit-breakers'] });
    },
  });

  const handleSubmitOrder = (e: React.FormEvent) => {
    e.preventDefault();
    const data: OrderSubmitRequest = {
      symbol: symbol.toUpperCase(),
      side,
      order_type: orderType,
      quantity_lots: Number(quantity),
    };
    if (orderType === 'LIMIT' && limitPrice) {
      data.limit_price = Number(limitPrice);
    }
    if (strategyId) {
      data.strategy_id = strategyId;
    }
    submitOrder.mutate(data);
  };

  const anyTripped = circuitBreakers.some((cb: CircuitBreakerStatus) => cb.is_tripped);

  // Chart data
  const equityChartData = pnlData.map((d: PnLResponse) => ({
    date: format(new Date(d.date), 'dd MMM'),
    total_equity: d.total_equity,
  }));

  const returnChartData = pnlData.map((d: PnLResponse) => ({
    date: format(new Date(d.date), 'dd MMM'),
    daily_return_pct: d.daily_return_pct,
  }));

  // Orders table columns
  const orderColumns = [
    { key: 'client_order_id', label: 'Order ID', render: (v: string) => <span className="font-mono text-xs">{v?.slice(0, 8)}...</span> },
    { key: 'symbol', label: 'Symbol', render: (v: string) => <span className="font-semibold text-slate-100">{v}</span> },
    {
      key: 'side',
      label: 'Side',
      render: (v: string) => (
        <span className={`font-semibold ${v === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
          {v}
        </span>
      ),
    },
    { key: 'order_type', label: 'Type' },
    { key: 'quantity', label: 'Qty', align: 'right' as const, sortable: true },
    { key: 'filled_quantity', label: 'Filled', align: 'right' as const, sortable: true },
    {
      key: 'limit_price',
      label: 'Limit Price',
      align: 'right' as const,
      render: (v: number | null) => (v != null ? v.toLocaleString('id-ID') : '--'),
    },
    {
      key: 'status',
      label: 'Status',
      render: (v: string) => <Badge variant={statusBadgeVariant(v)}>{v}</Badge>,
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (v: string) => (v ? format(new Date(v), 'dd MMM HH:mm') : '--'),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Live Trading">
        <div className="flex items-center gap-2">
          {anyTripped ? (
            <ShieldAlert className="h-4 w-4 text-red-400" />
          ) : (
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          )}
          <span className={`text-sm font-medium ${anyTripped ? 'text-red-400' : 'text-emerald-400'}`}>
            Circuit Breaker: {anyTripped ? 'TRIPPED' : 'OK'}
          </span>
          <span className={`h-2.5 w-2.5 rounded-full ${anyTripped ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} />
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Orders + P&L */}
        <div className="lg:col-span-2 space-y-6">
          {/* Orders Table */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-slate-100">Orders</h3>
              <div className="flex items-center gap-2">
                {ORDER_STATUSES.map((s) => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
                      statusFilter === s
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <DataTable
              columns={orderColumns}
              data={orders}
              loading={ordersLoading}
              emptyMessage="No orders found"
            />
          </div>

          {/* P&L Charts */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">P&L - Equity Curve</h3>
            {pnlLoading ? (
              <div className="flex items-center justify-center h-64">
                <LoadingSpinner label="Loading P&L..." />
              </div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={equityChartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
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
                    <Line
                      type="monotone"
                      dataKey="total_equity"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>

                <h3 className="text-base font-semibold text-slate-100 mt-6 mb-4">Daily Returns (%)</h3>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={returnChartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
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
                      formatter={((value: any) => [`${value.toFixed(2)}%`, 'Daily Return']) as any}
                    />
                    <Bar
                      dataKey="daily_return_pct"
                      fill="#3b82f6"
                      radius={[2, 2, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </>
            )}
          </div>
        </div>

        {/* Right Column - Order Form + Circuit Breakers */}
        <div className="space-y-6">
          {/* Order Submission Form */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">Submit Order</h3>
            <form onSubmit={handleSubmitOrder} className="space-y-4">
              {/* Symbol */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Symbol
                </label>
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  placeholder="e.g. BBCA"
                  required
                  className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
                />
              </div>

              {/* Side Toggle */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Side
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setSide('BUY')}
                    className={`py-2 text-sm font-semibold rounded-lg transition-colors ${
                      side === 'BUY'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : 'bg-slate-900/50 text-slate-400 border border-slate-700 hover:bg-slate-700/50'
                    }`}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setSide('SELL')}
                    className={`py-2 text-sm font-semibold rounded-lg transition-colors ${
                      side === 'SELL'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                        : 'bg-slate-900/50 text-slate-400 border border-slate-700 hover:bg-slate-700/50'
                    }`}
                  >
                    SELL
                  </button>
                </div>
              </div>

              {/* Order Type */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Order Type
                </label>
                <select
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value as 'MARKET' | 'LIMIT')}
                  className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
                >
                  <option value="MARKET">Market</option>
                  <option value="LIMIT">Limit</option>
                </select>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Quantity (lots)
                </label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="0"
                  min={1}
                  required
                  className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
                />
              </div>

              {/* Limit Price (conditional) */}
              {orderType === 'LIMIT' && (
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                    Limit Price
                  </label>
                  <input
                    type="number"
                    value={limitPrice}
                    onChange={(e) => setLimitPrice(e.target.value)}
                    placeholder="0"
                    min={0}
                    required
                    className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
                  />
                </div>
              )}

              {/* Strategy ID */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Strategy (optional)
                </label>
                <select
                  value={strategyId}
                  onChange={(e) => setStrategyId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
                >
                  <option value="">No strategy</option>
                  {strategies.map((s: Strategy) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={submitOrder.isPending || !symbol || !quantity}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold text-sm rounded-lg transition-colors"
              >
                {submitOrder.isPending ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Submit Order
              </button>

              {submitOrder.isError && (
                <p className="text-xs text-red-400 mt-1">
                  Failed to submit order. Please try again.
                </p>
              )}
              {submitOrder.isSuccess && (
                <p className="text-xs text-emerald-400 mt-1">
                  Order submitted successfully.
                </p>
              )}
            </form>
          </div>

          {/* Circuit Breakers */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">Circuit Breakers</h3>
            {cbLoading ? (
              <LoadingSpinner label="Loading..." />
            ) : circuitBreakers.length === 0 ? (
              <p className="text-sm text-slate-500">No circuit breakers configured.</p>
            ) : (
              <div className="space-y-3">
                {circuitBreakers.map((cb: CircuitBreakerStatus) => (
                  <div
                    key={cb.strategy_id}
                    className={`p-4 rounded-lg border ${
                      cb.is_tripped
                        ? 'border-red-500/30 bg-red-500/5'
                        : 'border-slate-700/50 bg-slate-900/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-100">
                        {cb.strategy_id}
                      </span>
                      <Badge variant={cb.is_tripped ? 'danger' : 'success'}>
                        {cb.is_tripped ? 'TRIPPED' : 'OK'}
                      </Badge>
                    </div>
                    {cb.is_tripped && (
                      <>
                        {cb.tripped_at && (
                          <p className="text-xs text-slate-500 mb-1">
                            Tripped: {format(new Date(cb.tripped_at), 'dd MMM yyyy HH:mm')}
                          </p>
                        )}
                        {cb.reason && (
                          <p className="text-xs text-red-400 mb-2">
                            Reason: {cb.reason}
                          </p>
                        )}
                        <button
                          onClick={() => resetCb.mutate(cb.strategy_id)}
                          disabled={resetCb.isPending}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
                        >
                          <RefreshCw className={`h-3 w-3 ${resetCb.isPending ? 'animate-spin' : ''}`} />
                          Clear
                        </button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
