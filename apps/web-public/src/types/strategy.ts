export interface StrategyResponse {
  id: string;
  name: string;
  strategy_type: string;
  is_enabled: boolean;
  parameters: Record<string, unknown>;
  risk_limits: Record<string, number>;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface StrategyPerformance {
  strategy_id: string;
  name: string;
  total_return_pct: number;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate: number | null;
  total_trades: number;
  avg_holding_period_days: number | null;
  period_start: string | null;
  period_end: string | null;
}
