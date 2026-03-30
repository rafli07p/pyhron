export interface BacktestResultResponse {
  task_id: string;
  status: string;
  strategy_name: string | null;
  symbols: string[] | null;
  start_date: string | null;
  end_date: string | null;
  initial_capital: number | null;
  final_capital: number | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface BacktestMetrics {
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
