import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const riskHandlers = [
  // Risk snapshot for a strategy
  http.get(`${API_BASE}/api/v1/live-trading-risk/risk/:strategyId/snapshot`, ({ params }) => {
    return HttpResponse.json({
      strategy_id: params.strategyId,
      timestamp: new Date().toISOString(),
      var_95: 12_500_000,
      var_99: 18_750_000,
      cvar_95: 15_800_000,
      cvar_99: 22_100_000,
      gross_exposure: 1_250_000_000,
      net_exposure: 480_000_000,
      long_exposure: 865_000_000,
      short_exposure: 385_000_000,
      leverage: 1.67,
      beta: 0.92,
      sector_concentration: {
        Financials: 0.42,
        'Consumer Staples': 0.18,
        Energy: 0.15,
        'Communication Services': 0.12,
        Industrials: 0.08,
        Other: 0.05,
      },
      top_positions_risk: [
        { symbol: 'BBCA', weight: 0.22, contribution_to_var: 0.31 },
        { symbol: 'BMRI', weight: 0.15, contribution_to_var: 0.19 },
        { symbol: 'ADRO', weight: 0.12, contribution_to_var: 0.14 },
      ],
      margin_utilization_pct: 58.3,
      drawdown_current_pct: -2.1,
      drawdown_max_pct: -8.3,
    });
  }),

  // Kill switch status
  http.get(`${API_BASE}/api/v1/live-trading-risk/kill-switch/status`, () => {
    return HttpResponse.json({
      status: 'ARMED',
      triggered: false,
      last_triggered_at: null,
      thresholds: {
        max_daily_loss: 50_000_000,
        max_drawdown_pct: 15.0,
        max_position_concentration_pct: 30.0,
        max_gross_leverage: 3.0,
      },
      current_values: {
        daily_loss: 3_200_000,
        drawdown_pct: 2.1,
        max_position_concentration_pct: 22.0,
        gross_leverage: 1.67,
      },
      armed_at: '2026-04-01T09:00:00Z',
      armed_by: 'demo@pyhron.com',
    });
  }),
];
