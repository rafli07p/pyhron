'use client';
import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useSearchParams } from 'next/navigation';
import { Play, RefreshCw, Clock, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface BacktestRequest {
  strategy_type: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  slippage_bps: number;
}

interface BacktestSubmission {
  task_id: string;
  status: string;
  submitted_at: string;
}

interface BacktestResult {
  task_id: string;
  status: string;
  strategy_name: string | null;
  symbols: string[] | null;
  start_date: string | null;
  end_date: string | null;
  initial_capital: string | null;
  final_capital: string | null;
  completed_at: string | null;
  error_message: string | null;
}

interface BacktestMetrics {
  task_id: string;
  total_return_pct: number;
  cagr_pct: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  max_drawdown_pct: number;
  max_drawdown_duration_days: number | null;
  win_rate_pct: number;
  profit_factor: number | null;
  omega_ratio: number | null;
  total_trades: number;
  cost_drag_annualized_pct: number | null;
}

interface BacktestHistoryEntry {
  task_id: string;
  strategy_name: string | null;
  status: string;
  submitted_at: string;
  total_return_pct: number | null;
  sharpe_ratio: number | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────
const IDX_UNIVERSE = [
  'BBCA', 'BBRI', 'BMRI', 'BBNI', 'TLKM',
  'ASII', 'GOTO', 'UNVR', 'BRIS', 'ARTO',
  'ICBP', 'INDF', 'KLBF', 'MAPI', 'PGAS',
  'PTBA', 'SMGR', 'TBIG', 'TOWR', 'BTPS',
];

const STRATEGY_TYPES = [
  { value: 'momentum', label: 'Momentum' },
  { value: 'mean_reversion', label: 'Mean Reversion' },
  { value: 'arbitrage', label: 'Arbitrage' },
  { value: 'ml_signal', label: 'ML Signal' },
];

// ── Formatters ────────────────────────────────────────────────────────────────
function fmtPct(v: number | null, decimals = 2): string {
  if (v === null || v === undefined) return '—';
  return (v >= 0 ? '+' : '') + v.toFixed(decimals) + '%';
}
function fmtNum(v: number | null, decimals = 2): string {
  if (v === null || v === undefined) return '—';
  return v.toFixed(decimals);
}
function fmtIDR(v: string | number | null): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  if (n >= 1e12) return 'Rp ' + (n / 1e12).toFixed(2) + 'T';
  if (n >= 1e9) return 'Rp ' + (n / 1e9).toFixed(2) + 'B';
  return 'Rp ' + n.toLocaleString('id-ID');
}
function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

// ── Status indicator ──────────────────────────────────────────────────────────
function StatusIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 size={14} style={{ color: 'var(--color-positive)' }} />;
  if (status === 'failed') return <XCircle size={14} style={{ color: 'var(--color-negative)' }} />;
  if (status === 'running') return <Loader2 size={14} style={{ color: 'var(--color-blue-primary)', animation: 'spin 1s linear infinite' }} />;
  return <Clock size={14} style={{ color: 'var(--color-text-muted)' }} />;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; fg: string }> = {
    completed: { bg: 'rgba(5,122,85,0.08)', fg: '#057a55' },
    failed: { bg: 'rgba(220,38,38,0.08)', fg: '#dc2626' },
    running: { bg: 'rgba(0,87,168,0.08)', fg: 'var(--color-blue-primary)' },
    submitted: { bg: 'rgba(217,119,6,0.08)', fg: '#d97706' },
  };
  const c = map[status] ?? { bg: 'rgba(107,114,128,0.08)', fg: '#6b7280' };
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: '0.06em',
      background: c.bg, color: c.fg,
    }}>
      {status}
    </span>
  );
}

// ── Metric Card ────────────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, positive }: { label: string; value: string; sub?: string; positive?: boolean }) {
  return (
    <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, padding: '14px 18px' }}>
      <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 6 }}>
        {label}
      </p>
      <p style={{
        fontSize: 20, fontWeight: 700, margin: 0,
        color: positive === undefined ? 'var(--color-text-primary)' : positive ? 'var(--color-positive)' : 'var(--color-negative)',
      }}>
        {value}
      </p>
      {sub && <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 3 }}>{sub}</p>}
    </div>
  );
}

// ── Main Page Content ─────────────────────────────────────────────────────────
function StudioPageContent() {
  const { data: session } = useSession();
  const searchParams = useSearchParams();
  const strategyFromUrl = searchParams.get('strategy');

  // Form state
  const [strategyType, setStrategyType] = useState('momentum');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII']);
  const [startDate, setStartDate] = useState('2022-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [capital, setCapital] = useState('1000000000');
  const [slippage, setSlippage] = useState('5');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Result state
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [metrics, setMetrics] = useState<BacktestMetrics | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // History
  const [history, setHistory] = useState<BacktestHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null);
  const [historyMetrics, setHistoryMetrics] = useState<Record<string, BacktestMetrics>>({});

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  // Note which strategy was passed via URL (pre-fill future enhancement)
  useEffect(() => {
    if (strategyFromUrl) {
      // strategyFromUrl is a strategy id, reserved for future pre-fill
    }
  }, [strategyFromUrl]);

  // Fetch history (declared before pollTask which calls it)
  const fetchHistory = useCallback(async () => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    if (!token) return;
    setHistoryLoading(true);
    try {
      const res = await fetch('/api/v1/backtest/history', { headers: authHeader() });
      if (res.ok) setHistory(await res.json());
    } catch { /* noop */ }
    finally { setHistoryLoading(false); }
  }, [session, authHeader]);

  // Poll active task
  const pollTask = useCallback(async (taskId: string) => {
    try {
      const res = await fetch(`/api/v1/backtest/${taskId}`, { headers: authHeader() });
      if (!res.ok) return;
      const data: BacktestResult = await res.json();
      setResult(data);
      if (data.status === 'completed') {
        // Fetch metrics
        const mr = await fetch(`/api/v1/backtest/${taskId}/metrics`, { headers: authHeader() });
        if (mr.ok) setMetrics(await mr.json());
        if (pollRef.current) clearInterval(pollRef.current);
        setPolling(false);
        fetchHistory();
      } else if (data.status === 'failed') {
        if (pollRef.current) clearInterval(pollRef.current);
        setPolling(false);
      }
    } catch { /* noop */ }
  }, [authHeader, fetchHistory]);

  useEffect(() => {
    if (activeTaskId && polling) {
      pollRef.current = setInterval(() => pollTask(activeTaskId), 2000);
      return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }
  }, [activeTaskId, polling, pollTask]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const submitBacktest = async () => {
    if (selectedSymbols.length === 0) { setFormError('Select at least one symbol'); return; }
    if (!startDate || !endDate) { setFormError('Start and end dates are required'); return; }
    if (new Date(startDate) >= new Date(endDate)) { setFormError('Start date must be before end date'); return; }
    setFormError('');
    setSubmitting(true);
    setResult(null);
    setMetrics(null);
    try {
      const body: BacktestRequest = {
        strategy_type: strategyType,
        symbols: selectedSymbols,
        start_date: startDate,
        end_date: endDate,
        initial_capital: Number(capital),
        slippage_bps: Number(slippage),
      };
      const res = await fetch('/api/v1/backtest/run', {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const submission: BacktestSubmission = await res.json();
      setActiveTaskId(submission.task_id);
      setPolling(true);
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleSymbol = (sym: string) => {
    setSelectedSymbols(prev =>
      prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym]
    );
  };

  const loadHistoryMetrics = async (taskId: string) => {
    if (historyMetrics[taskId]) {
      setExpandedHistory(prev => prev === taskId ? null : taskId);
      return;
    }
    try {
      const res = await fetch(`/api/v1/backtest/${taskId}/metrics`, { headers: authHeader() });
      if (res.ok) {
        const m: BacktestMetrics = await res.json();
        setHistoryMetrics(prev => ({ ...prev, [taskId]: m }));
      }
    } catch { /* noop */ }
    setExpandedHistory(prev => prev === taskId ? null : taskId);
  };

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 2 }}>
            Strategy Studio
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Backtest and validate trading strategies against IDX historical data
          </p>
        </div>
        <button
          type="button"
          onClick={fetchHistory}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            background: 'white', color: 'var(--color-text-secondary)',
            border: '1px solid var(--color-border)', cursor: 'pointer',
          }}
        >
          <RefreshCw size={12} />
          Refresh History
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left: Config panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                Backtest Configuration
              </span>
            </div>
            <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Strategy type */}
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 5 }}>
                  Strategy Type
                </label>
                <select
                  value={strategyType}
                  onChange={e => setStrategyType(e.target.value)}
                  style={{
                    width: '100%', padding: '7px 10px', borderRadius: 6, fontSize: 13,
                    border: '1px solid var(--color-border)', outline: 'none',
                    background: 'var(--color-bg-page)', boxSizing: 'border-box',
                  }}
                >
                  {STRATEGY_TYPES.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>

              {/* Date range */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 5 }}>
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                    style={{
                      width: '100%', padding: '7px 10px', borderRadius: 6, fontSize: 12,
                      border: '1px solid var(--color-border)', outline: 'none',
                      background: 'var(--color-bg-page)', boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 5 }}>
                    End Date
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={e => setEndDate(e.target.value)}
                    style={{
                      width: '100%', padding: '7px 10px', borderRadius: 6, fontSize: 12,
                      border: '1px solid var(--color-border)', outline: 'none',
                      background: 'var(--color-bg-page)', boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              {/* Capital & Slippage */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 5 }}>
                    Initial Capital (IDR)
                  </label>
                  <input
                    type="number"
                    value={capital}
                    onChange={e => setCapital(e.target.value)}
                    min="1000000"
                    step="1000000"
                    style={{
                      width: '100%', padding: '7px 10px', borderRadius: 6, fontSize: 12,
                      border: '1px solid var(--color-border)', outline: 'none',
                      background: 'var(--color-bg-page)', boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 5 }}>
                    Slippage (bps)
                  </label>
                  <input
                    type="number"
                    value={slippage}
                    onChange={e => setSlippage(e.target.value)}
                    min="0"
                    max="100"
                    step="0.5"
                    style={{
                      width: '100%', padding: '7px 10px', borderRadius: 6, fontSize: 12,
                      border: '1px solid var(--color-border)', outline: 'none',
                      background: 'var(--color-bg-page)', boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              {/* Symbol selector */}
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 5 }}>
                  Universe ({selectedSymbols.length} selected)
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {IDX_UNIVERSE.map(sym => {
                    const sel = selectedSymbols.includes(sym);
                    return (
                      <button
                        key={sym}
                        type="button"
                        onClick={() => toggleSymbol(sym)}
                        style={{
                          padding: '3px 9px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                          border: `1px solid ${sel ? 'var(--color-blue-primary)' : 'var(--color-border)'}`,
                          background: sel ? 'var(--color-blue-primary)' : 'white',
                          color: sel ? 'white' : 'var(--color-text-secondary)',
                          cursor: 'pointer', fontFamily: 'monospace',
                        }}
                      >
                        {sym}
                      </button>
                    );
                  })}
                </div>
              </div>

              {formError && (
                <p style={{ fontSize: 12, color: 'var(--color-negative)', margin: 0 }}>{formError}</p>
              )}

              <button
                type="button"
                onClick={submitBacktest}
                disabled={submitting || polling}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  padding: '10px 16px', borderRadius: 6, fontSize: 13, fontWeight: 700,
                  background: submitting || polling ? 'rgba(0,87,168,0.5)' : 'var(--color-blue-primary)',
                  color: 'white', border: 'none',
                  cursor: submitting || polling ? 'not-allowed' : 'pointer',
                  width: '100%',
                }}
              >
                {polling ? (
                  <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Running Backtest...</>
                ) : (
                  <><Play size={14} /> Run Backtest</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Results panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Active result */}
          {(result || polling) && (
            <div>
              {/* Status bar */}
              <div style={{
                background: '#fff', border: '1px solid var(--color-border)',
                borderRadius: 8, padding: '12px 16px',
                display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14,
              }}>
                {result ? <StatusIcon status={result.status} /> : <Loader2 size={14} style={{ color: 'var(--color-blue-primary)', animation: 'spin 1s linear infinite' }} />}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {result?.status === 'completed' ? 'Backtest Completed' :
                     result?.status === 'failed' ? 'Backtest Failed' :
                     'Running Backtest...'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                    {activeTaskId ? `Task ID: ${activeTaskId.slice(0, 8)}...` : ''}
                    {result?.completed_at ? ` · Completed ${fmtDateTime(result.completed_at)}` : ''}
                  </div>
                </div>
                {result && <StatusBadge status={result.status} />}
              </div>

              {/* Error */}
              {result?.status === 'failed' && result.error_message && (
                <div style={{
                  background: 'rgba(220,38,38,0.04)', border: '1px solid rgba(220,38,38,0.2)',
                  borderRadius: 8, padding: '12px 16px', marginBottom: 14,
                }}>
                  <p style={{ fontSize: 12, color: '#dc2626', margin: 0 }}>{result.error_message}</p>
                </div>
              )}

              {/* Metrics grid */}
              {metrics && (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
                    <MetricCard
                      label="Total Return"
                      value={fmtPct(metrics.total_return_pct)}
                      positive={metrics.total_return_pct >= 0}
                    />
                    <MetricCard
                      label="CAGR"
                      value={fmtPct(metrics.cagr_pct)}
                      positive={metrics.cagr_pct !== null ? metrics.cagr_pct >= 0 : undefined}
                    />
                    <MetricCard
                      label="Sharpe Ratio"
                      value={fmtNum(metrics.sharpe_ratio)}
                      positive={metrics.sharpe_ratio !== null ? metrics.sharpe_ratio >= 1 : undefined}
                    />
                    <MetricCard
                      label="Max Drawdown"
                      value={fmtPct(metrics.max_drawdown_pct !== null ? -Math.abs(metrics.max_drawdown_pct) : null)}
                      positive={false}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
                    <MetricCard label="Sortino" value={fmtNum(metrics.sortino_ratio)} />
                    <MetricCard label="Calmar" value={fmtNum(metrics.calmar_ratio)} />
                    <MetricCard label="Omega" value={fmtNum(metrics.omega_ratio)} />
                    <MetricCard label="Profit Factor" value={fmtNum(metrics.profit_factor)} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                    <MetricCard label="Win Rate" value={fmtPct(metrics.win_rate_pct)} positive={metrics.win_rate_pct >= 50} />
                    <MetricCard label="Total Trades" value={String(metrics.total_trades)} />
                    <MetricCard label="DD Duration" value={metrics.max_drawdown_duration_days !== null ? `${metrics.max_drawdown_duration_days}d` : '—'} />
                    <MetricCard label="Cost Drag" value={fmtPct(metrics.cost_drag_annualized_pct)} positive={false} />
                  </div>

                  {/* Capital summary */}
                  <div style={{
                    marginTop: 14, background: '#fff', border: '1px solid var(--color-border)',
                    borderRadius: 8, padding: '12px 16px',
                    display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16,
                  }}>
                    {[
                      { label: 'Initial Capital', value: fmtIDR(result?.initial_capital ?? null) },
                      { label: 'Final Capital', value: fmtIDR(result?.final_capital ?? null) },
                      { label: 'Period', value: result?.start_date && result?.end_date ? `${result.start_date} → ${result.end_date}` : '—' },
                    ].map(({ label, value }) => (
                      <div key={label}>
                        <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', marginBottom: 3 }}>{label}</p>
                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>{value}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Empty state */}
          {!result && !polling && (
            <div style={{
              background: '#fff', border: '1px solid var(--color-border)',
              borderRadius: 8, padding: '60px 40px', textAlign: 'center',
            }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
              <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 6 }}>
                Configure and run a backtest
              </p>
              <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                Select your strategy parameters on the left, then click Run Backtest to see results.
              </p>
            </div>
          )}

          {/* History */}
          <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-page)' }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                Backtest History
              </span>
            </div>
            {historyLoading ? (
              <div style={{ padding: 30, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 12 }}>Loading...</div>
            ) : history.length === 0 ? (
              <div style={{ padding: 30, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 12 }}>No backtest runs yet</div>
            ) : (
              <div>
                {history.map((h, i) => {
                  const hm = historyMetrics[h.task_id];
                  return (
                  <div key={h.task_id}>
                    <div
                      style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '10px 16px', cursor: 'pointer',
                        borderBottom: '1px solid var(--color-border-subtle)',
                        background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)',
                      }}
                      onClick={() => h.status === 'completed' ? loadHistoryMetrics(h.task_id) : undefined}
                    >
                      <StatusIcon status={h.status} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {h.strategy_name ?? 'Unnamed'}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                          {fmtDateTime(h.submitted_at)} · {h.task_id.slice(0, 8)}...
                        </div>
                      </div>
                      <StatusBadge status={h.status} />
                      {h.total_return_pct !== null && (
                        <span style={{
                          fontSize: 12, fontWeight: 700,
                          color: h.total_return_pct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)',
                        }}>
                          {fmtPct(h.total_return_pct)}
                        </span>
                      )}
                      {h.sharpe_ratio !== null && (
                        <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                          SR {fmtNum(h.sharpe_ratio)}
                        </span>
                      )}
                      {h.status === 'completed' && (
                        expandedHistory === h.task_id
                          ? <ChevronUp size={13} style={{ color: 'var(--color-text-muted)' }} />
                          : <ChevronDown size={13} style={{ color: 'var(--color-text-muted)' }} />
                      )}
                    </div>
                    {/* Expanded metrics */}
                    {expandedHistory === h.task_id && hm && (
                      <div style={{
                        padding: '12px 16px', background: 'rgba(0,87,168,0.03)',
                        borderBottom: '1px solid var(--color-border-subtle)',
                        display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 10,
                      }}>
                        {[
                          { label: 'CAGR', value: fmtPct(hm.cagr_pct) },
                          { label: 'Sharpe', value: fmtNum(hm.sharpe_ratio) },
                          { label: 'Sortino', value: fmtNum(hm.sortino_ratio) },
                          { label: 'Max DD', value: fmtPct(-Math.abs(hm.max_drawdown_pct)) },
                          { label: 'Win Rate', value: fmtPct(hm.win_rate_pct) },
                          { label: 'Trades', value: String(hm.total_trades) },
                        ].map(({ label, value }) => (
                          <div key={label}>
                            <p style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-text-muted)', marginBottom: 2 }}>{label}</p>
                            <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>{value}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Page wrapper with Suspense for useSearchParams ────────────────────────────
export default function StudioPage() {
  return (
    <Suspense fallback={<div style={{ padding: 24, fontSize: 13, color: 'var(--color-text-muted)' }}>Loading…</div>}>
      <StudioPageContent />
    </Suspense>
  );
}
