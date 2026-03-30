export interface PositionResponse {
  symbol: string;
  exchange: string;
  strategy_id: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  market_value: number;
  weight_pct: number;
}

export interface OrderResponse {
  client_order_id: string;
  strategy_id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  filled_quantity: number;
  limit_price: number | null;
  status: string;
  created_at: string;
}

export interface PaperSessionResponse {
  id: string;
  name: string;
  strategy_id: string;
  status: string;
  mode: string;
  initial_capital_idr: number;
  current_nav_idr: number;
  peak_nav_idr: number;
  max_drawdown_pct: number;
  total_trades: number;
  winning_trades: number;
  realized_pnl_idr: number;
  total_commission_idr: number;
  cash_idr: number;
  unsettled_cash_idr: number;
}

export interface RiskSnapshotResponse {
  strategy_id: string;
  timestamp: string;
  nav_idr: number;
  exposure: {
    gross_exposure_idr: number;
    net_exposure_idr: number;
    long_exposure_idr: number;
    short_exposure_idr: number;
    beta_vs_ihsg: number;
  };
  concentration: {
    sector_hhi: number;
    top5_weight_pct: number;
    largest_position_pct: number;
    largest_position_symbol: string;
    num_positions: number;
  };
  var: {
    var_1d_95_idr: number;
    var_5d_95_idr: number;
    var_1d_99_idr: number;
    component_var: Record<string, number>;
  };
  daily_loss_pct: number;
  drawdown_pct: number;
  kill_switch_state: string;
}
