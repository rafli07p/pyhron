import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const strategies = [
  {
    id: 'strat-001',
    name: 'MomentumIDX',
    description: 'Cross-sectional momentum strategy on IDX LQ45 constituents',
    status: 'active',
    universe: 'LQ45',
    rebalance_freq: 'weekly',
    capital_allocated: 500_000_000,
    created_at: '2025-06-15T08:00:00Z',
    updated_at: '2026-04-01T16:00:00Z',
  },
  {
    id: 'strat-002',
    name: 'PairsTrade',
    description: 'Statistical arbitrage pairs trading on banking sector',
    status: 'active',
    universe: 'Banking',
    rebalance_freq: 'daily',
    capital_allocated: 300_000_000,
    created_at: '2025-08-01T08:00:00Z',
    updated_at: '2026-04-01T16:00:00Z',
  },
  {
    id: 'strat-003',
    name: 'MeanReversion',
    description: 'Intraday mean-reversion on high-volume IDX stocks',
    status: 'paused',
    universe: 'IDX30',
    rebalance_freq: 'intraday',
    capital_allocated: 200_000_000,
    created_at: '2025-10-10T08:00:00Z',
    updated_at: '2026-03-28T12:00:00Z',
  },
  {
    id: 'strat-004',
    name: 'MLSignalAlpha',
    description: 'ML-driven alpha signals combining fundamental and technical factors',
    status: 'active',
    universe: 'LQ45',
    rebalance_freq: 'daily',
    capital_allocated: 750_000_000,
    created_at: '2025-12-01T08:00:00Z',
    updated_at: '2026-04-01T16:00:00Z',
  },
];

const performanceByStrategy: Record<string, object> = {
  'strat-001': {
    total_return_pct: 18.7,
    annualized_return_pct: 22.4,
    sharpe_ratio: 1.65,
    sortino_ratio: 2.12,
    max_drawdown_pct: -8.3,
    win_rate: 0.58,
    profit_factor: 1.82,
    avg_trade_pnl: 1_250_000,
    total_trades: 347,
    calmar_ratio: 2.7,
  },
  'strat-002': {
    total_return_pct: 12.4,
    annualized_return_pct: 14.9,
    sharpe_ratio: 2.01,
    sortino_ratio: 2.85,
    max_drawdown_pct: -4.1,
    win_rate: 0.64,
    profit_factor: 2.15,
    avg_trade_pnl: 820_000,
    total_trades: 512,
    calmar_ratio: 3.63,
  },
  'strat-003': {
    total_return_pct: 6.2,
    annualized_return_pct: 7.4,
    sharpe_ratio: 0.92,
    sortino_ratio: 1.15,
    max_drawdown_pct: -11.5,
    win_rate: 0.51,
    profit_factor: 1.24,
    avg_trade_pnl: 310_000,
    total_trades: 1283,
    calmar_ratio: 0.64,
  },
  'strat-004': {
    total_return_pct: 24.1,
    annualized_return_pct: 28.9,
    sharpe_ratio: 1.94,
    sortino_ratio: 2.68,
    max_drawdown_pct: -6.8,
    win_rate: 0.61,
    profit_factor: 2.04,
    avg_trade_pnl: 1_780_000,
    total_trades: 215,
    calmar_ratio: 4.25,
  },
};

export const strategyHandlers = [
  // List strategies
  http.get(`${API_BASE}/v1/strategies/`, () => {
    return HttpResponse.json({ strategies, total: strategies.length });
  }),

  // Single strategy
  http.get(`${API_BASE}/v1/strategies/:id`, ({ params }) => {
    const strat = strategies.find((s) => s.id === params.id);
    if (!strat) {
      return HttpResponse.json({ detail: 'Strategy not found' }, { status: 404 });
    }
    return HttpResponse.json(strat);
  }),

  // Create strategy
  http.post(`${API_BASE}/v1/strategies/`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: `strat-${Date.now()}`,
        name: body.name,
        description: body.description || '',
        status: 'draft',
        universe: body.universe || 'LQ45',
        rebalance_freq: body.rebalance_freq || 'daily',
        capital_allocated: body.capital_allocated || 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  // Strategy performance
  http.get(`${API_BASE}/v1/strategies/:id/performance`, ({ params }) => {
    const perf = performanceByStrategy[params.id as string];
    if (!perf) {
      return HttpResponse.json({ detail: 'Strategy not found' }, { status: 404 });
    }
    return HttpResponse.json({
      strategy_id: params.id,
      ...perf,
      as_of: new Date().toISOString(),
    });
  }),
];
