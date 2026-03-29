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
} from 'recharts';
import {
  Plus,
  Play,
  Square,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Activity,
  X,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { paperTradingApi, strategyApi } from '../../api/endpoints';
import type {
  PaperSession,
  PaperNavSnapshot,
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

function statusBadgeVariant(
  status: string,
): 'success' | 'danger' | 'warning' | 'info' | 'neutral' {
  switch (status.toUpperCase()) {
    case 'RUNNING':
      return 'success';
    case 'STOPPED':
    case 'COMPLETED':
      return 'danger';
    case 'PAUSED':
      return 'warning';
    case 'CREATED':
    case 'PENDING':
      return 'info';
    default:
      return 'neutral';
  }
}

function SessionNavChart({ sessionId }: { sessionId: string }) {
  const { data: navData = [], isLoading } = useQuery({
    queryKey: ['session-nav', sessionId],
    queryFn: () =>
      paperTradingApi.sessionNav(sessionId, { limit: 100 }).then((r) => r.data),
  });

  const chartData = navData.map((d: PaperNavSnapshot) => ({
    date: format(new Date(d.timestamp), 'dd MMM HH:mm'),
    nav: d.nav_idr,
    drawdown: d.drawdown_pct,
  }));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <LoadingSpinner label="Loading NAV..." size="sm" />
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <p className="text-sm text-slate-500 text-center py-8">
        No NAV data available yet.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#94a3b8', fontSize: 10 }}
          axisLine={{ stroke: '#475569' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#94a3b8', fontSize: 10 }}
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
            fontSize: 12,
          }}
          formatter={((value: any, name: string) => [
            name === 'nav' ? formatIdr(value) : `${value.toFixed(2)}%`,
            name === 'nav' ? 'NAV' : 'Drawdown',
          ]) as any}
        />
        <Line type="monotone" dataKey="nav" stroke="#3b82f6" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function PaperTradingPage() {
  const queryClient = useQueryClient();
  const [showNewSession, setShowNewSession] = useState(false);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);

  // New session form state
  const [newName, setNewName] = useState('');
  const [newStrategyId, setNewStrategyId] = useState('');
  const [newCapital, setNewCapital] = useState('');
  const [newMode, setNewMode] = useState('backfill');

  // Queries
  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ['paper-sessions'],
    queryFn: () => paperTradingApi.listSessions().then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list().then((r) => r.data),
  });

  // Mutations
  const createSession = useMutation({
    mutationFn: (data: {
      name: string;
      strategy_id: string;
      initial_capital_idr: number;
      mode?: string;
    }) => paperTradingApi.createSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-sessions'] });
      setShowNewSession(false);
      setNewName('');
      setNewStrategyId('');
      setNewCapital('');
      setNewMode('backfill');
    },
  });

  const startSession = useMutation({
    mutationFn: (id: string) => paperTradingApi.startSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-sessions'] });
    },
  });

  const stopSession = useMutation({
    mutationFn: (id: string) => paperTradingApi.stopSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-sessions'] });
    },
  });

  const deleteSession = useMutation({
    mutationFn: (id: string) => paperTradingApi.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-sessions'] });
    },
  });

  const handleCreateSession = (e: React.FormEvent) => {
    e.preventDefault();
    createSession.mutate({
      name: newName,
      strategy_id: newStrategyId,
      initial_capital_idr: Number(newCapital),
      mode: newMode,
    });
  };

  const getPnlPct = (session: PaperSession) => {
    if (session.initial_capital_idr <= 0) return 0;
    return (
      ((session.current_nav_idr - session.initial_capital_idr) /
        session.initial_capital_idr) *
      100
    );
  };

  const getWinRate = (session: PaperSession) => {
    if (session.total_trades <= 0) return 0;
    return (session.winning_trades / session.total_trades) * 100;
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Paper Trading" subtitle="Simulate strategies with virtual capital">
        <button
          onClick={() => setShowNewSession(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Session
        </button>
      </PageHeader>

      {/* Consumer Health Indicator */}
      <div className="flex items-center gap-2 text-sm">
        <Activity className="h-4 w-4 text-slate-400" />
        <span className="text-slate-400">Paper Trading Engine</span>
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        <span className="text-emerald-400 text-xs font-medium">Healthy</span>
      </div>

      {/* New Session Dialog */}
      {showNewSession && (
        <div className="rounded-xl border border-blue-500/30 bg-slate-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-slate-100">
              Create New Session
            </h3>
            <button
              onClick={() => setShowNewSession(false)}
              className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <form onSubmit={handleCreateSession} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Session Name
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Momentum Test v2"
                required
                className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Strategy
              </label>
              <select
                value={newStrategyId}
                onChange={(e) => setNewStrategyId(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
              >
                <option value="">Select strategy</option>
                {strategies.map((s: Strategy) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Initial Capital (IDR)
              </label>
              <input
                type="number"
                value={newCapital}
                onChange={(e) => setNewCapital(e.target.value)}
                placeholder="e.g. 1000000000"
                min={0}
                required
                className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Mode
              </label>
              <select
                value={newMode}
                onChange={(e) => setNewMode(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
              >
                <option value="backfill">Backfill</option>
                <option value="live">Live</option>
                <option value="replay">Replay</option>
              </select>
            </div>
            <div className="sm:col-span-2 flex items-center gap-3">
              <button
                type="submit"
                disabled={createSession.isPending}
                className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                {createSession.isPending && <LoadingSpinner size="sm" />}
                Create Session
              </button>
              {createSession.isError && (
                <p className="text-xs text-red-400">Failed to create session.</p>
              )}
            </div>
          </form>
        </div>
      )}

      {/* Sessions Grid */}
      {sessionsLoading ? (
        <div className="flex items-center justify-center py-16">
          <LoadingSpinner label="Loading sessions..." />
        </div>
      ) : sessions.length === 0 ? (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-12 text-center">
          <p className="text-sm text-slate-500">
            No paper trading sessions yet. Create one to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {sessions.map((session: PaperSession) => {
            const pnlPct = getPnlPct(session);
            const winRate = getWinRate(session);
            const isExpanded = expandedSession === session.id;

            return (
              <div
                key={session.id}
                className="rounded-xl border border-slate-700 bg-slate-800 overflow-hidden"
              >
                {/* Card Header */}
                <div
                  className="p-5 cursor-pointer hover:bg-slate-800/80 transition-colors"
                  onClick={() =>
                    setExpandedSession(isExpanded ? null : session.id)
                  }
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <h4 className="text-sm font-semibold text-slate-100">
                        {session.name}
                      </h4>
                      <Badge variant={statusBadgeVariant(session.status)}>
                        {session.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Session Stats Grid */}
                  <div className="grid grid-cols-4 gap-3">
                    <div>
                      <p className="text-xs text-slate-500">Mode</p>
                      <p className="text-sm font-medium text-slate-300 capitalize">
                        {session.mode}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Initial Capital</p>
                      <p className="text-sm font-medium text-slate-300">
                        {formatIdr(session.initial_capital_idr)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Current NAV</p>
                      <p className="text-sm font-medium text-slate-300">
                        {formatIdr(session.current_nav_idr)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">P&L</p>
                      <p
                        className={`text-sm font-semibold ${
                          pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'
                        }`}
                      >
                        {pnlPct >= 0 ? '+' : ''}
                        {pnlPct.toFixed(2)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Max Drawdown</p>
                      <p className="text-sm font-medium text-red-400">
                        {session.max_drawdown_pct.toFixed(2)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Total Trades</p>
                      <p className="text-sm font-medium text-slate-300">
                        {session.total_trades}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Win Rate</p>
                      <p className="text-sm font-medium text-slate-300">
                        {winRate.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Strategy</p>
                      <p className="text-sm font-medium text-slate-300 truncate">
                        {strategies.find((s: Strategy) => s.id === session.strategy_id)
                          ?.name ?? session.strategy_id.slice(0, 8)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="px-5 pb-4 flex items-center gap-2">
                  {(session.status === 'CREATED' || session.status === 'created') && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        startSession.mutate(session.id);
                      }}
                      disabled={startSession.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 rounded-lg transition-colors"
                    >
                      <Play className="h-3 w-3" />
                      Start
                    </button>
                  )}
                  {(session.status === 'RUNNING' || session.status === 'running') && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          stopSession.mutate(session.id);
                        }}
                        disabled={stopSession.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/30 rounded-lg transition-colors"
                      >
                        <Square className="h-3 w-3" />
                        Stop
                      </button>
                    </>
                  )}
                  {(session.status === 'PAUSED' || session.status === 'paused') && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startSession.mutate(session.id);
                        }}
                        disabled={startSession.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 rounded-lg transition-colors"
                      >
                        <RotateCcw className="h-3 w-3" />
                        Resume
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          stopSession.mutate(session.id);
                        }}
                        disabled={stopSession.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/30 rounded-lg transition-colors"
                      >
                        <Square className="h-3 w-3" />
                        Stop
                      </button>
                    </>
                  )}
                  {(session.status === 'STOPPED' ||
                    session.status === 'stopped' ||
                    session.status === 'COMPLETED' ||
                    session.status === 'completed') && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (
                          window.confirm(
                            'Are you sure you want to delete this session?',
                          )
                        ) {
                          deleteSession.mutate(session.id);
                        }
                      }}
                      disabled={deleteSession.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
                    >
                      <X className="h-3 w-3" />
                      Delete
                    </button>
                  )}
                </div>

                {/* Expanded NAV Chart */}
                {isExpanded && (
                  <div className="border-t border-slate-700 p-5">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                      NAV History
                    </h5>
                    <SessionNavChart sessionId={session.id} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
