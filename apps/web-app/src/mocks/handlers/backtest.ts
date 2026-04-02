import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const backtestHistory = [
  {
    task_id: 'bt-20260401-001',
    strategy_name: 'MomentumIDX',
    status: 'completed',
    start_date: '2025-01-01',
    end_date: '2025-12-31',
    submitted_at: '2026-04-01T14:00:00Z',
    completed_at: '2026-04-01T14:03:22Z',
  },
  {
    task_id: 'bt-20260401-002',
    strategy_name: 'PairsTrade',
    status: 'completed',
    start_date: '2025-06-01',
    end_date: '2025-12-31',
    submitted_at: '2026-04-01T11:30:00Z',
    completed_at: '2026-04-01T11:32:15Z',
  },
  {
    task_id: 'bt-20260331-001',
    strategy_name: 'MLSignalAlpha',
    status: 'completed',
    start_date: '2024-01-01',
    end_date: '2025-12-31',
    submitted_at: '2026-03-31T09:00:00Z',
    completed_at: '2026-03-31T09:08:44Z',
  },
  {
    task_id: 'bt-20260330-001',
    strategy_name: 'MeanReversion',
    status: 'failed',
    start_date: '2025-01-01',
    end_date: '2025-12-31',
    submitted_at: '2026-03-30T15:20:00Z',
    completed_at: '2026-03-30T15:20:45Z',
    error: 'Insufficient data for symbol BREN in requested period',
  },
  {
    task_id: 'bt-20260329-001',
    strategy_name: 'MomentumIDX',
    status: 'completed',
    start_date: '2024-06-01',
    end_date: '2025-06-30',
    submitted_at: '2026-03-29T10:00:00Z',
    completed_at: '2026-03-29T10:04:11Z',
  },
];

function generateEquityCurve(days: number) {
  const curve = [];
  const now = new Date();
  let equity = 500_000_000;
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;
    const dailyReturn = (Math.random() - 0.46) * 0.02;
    equity = Math.round(equity * (1 + dailyReturn));
    curve.push({ date: date.toISOString().slice(0, 10), equity });
  }
  return curve;
}

export const backtestHandlers = [
  // Submit backtest
  http.post(`${API_BASE}/v1/backtest/run`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        task_id: `bt-${Date.now()}`,
        strategy_name: body.strategy_name || 'Unnamed',
        status: 'pending',
        start_date: body.start_date,
        end_date: body.end_date,
        submitted_at: new Date().toISOString(),
      },
      { status: 202 },
    );
  }),

  // Backtest result
  http.get(`${API_BASE}/v1/backtest/:taskId`, ({ params }) => {
    const found = backtestHistory.find((b) => b.task_id === params.taskId);
    if (found) {
      return HttpResponse.json(found);
    }
    return HttpResponse.json({
      task_id: params.taskId,
      strategy_name: 'MomentumIDX',
      status: 'completed',
      start_date: '2025-01-01',
      end_date: '2025-12-31',
      submitted_at: '2026-04-01T14:00:00Z',
      completed_at: '2026-04-01T14:03:22Z',
      equity_curve: generateEquityCurve(252),
    });
  }),

  // Backtest metrics
  http.get(`${API_BASE}/v1/backtest/:taskId/metrics`, ({ params }) => {
    return HttpResponse.json({
      task_id: params.taskId,
      status: 'completed',
      metrics: {
        total_return_pct: 23.4,
        annualized_return_pct: 23.4,
        sharpe_ratio: 1.84,
        sortino_ratio: 2.51,
        max_drawdown_pct: -7.2,
        calmar_ratio: 3.25,
        win_rate: 0.59,
        profit_factor: 1.95,
        total_trades: 428,
        avg_trade_pnl: 1_350_000,
        avg_holding_period_days: 4.2,
        turnover_annual: 8.7,
        beta: 0.85,
        alpha_annualized_pct: 14.2,
        information_ratio: 1.52,
        volatility_annualized_pct: 12.7,
        skewness: -0.32,
        kurtosis: 3.8,
      },
      equity_curve: generateEquityCurve(252),
      monthly_returns: [
        { month: '2025-01', return_pct: 2.1 },
        { month: '2025-02', return_pct: -0.8 },
        { month: '2025-03', return_pct: 3.4 },
        { month: '2025-04', return_pct: 1.7 },
        { month: '2025-05', return_pct: -1.2 },
        { month: '2025-06', return_pct: 4.1 },
        { month: '2025-07', return_pct: 2.3 },
        { month: '2025-08', return_pct: -0.5 },
        { month: '2025-09', return_pct: 1.9 },
        { month: '2025-10', return_pct: 3.6 },
        { month: '2025-11', return_pct: 2.8 },
        { month: '2025-12', return_pct: 1.4 },
      ],
    });
  }),

  // Backtest history
  http.get(`${API_BASE}/v1/backtest/history`, () => {
    return HttpResponse.json({ backtests: backtestHistory, total: backtestHistory.length });
  }),
];
