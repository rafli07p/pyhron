// Auth
export interface LoginRequest { email: string; password: string }
export interface RegisterRequest { email: string; password: string; full_name: string }
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; expires_in: number }
export interface UserProfile { id: string; email: string; full_name: string; is_active: boolean; role: string; tenant_id: string; created_at: string }

// Market
export interface MarketOverview { index_name: string; last_value: number; change: number; change_pct: number; volume: number; value_traded: number; advances: number; declines: number; unchanged: number; timestamp: string }
export interface OHLCVBar { timestamp: string; open: number; high: number; low: number; close: number; volume: number; value?: number }
export interface Instrument { symbol: string; name: string; exchange: string; sector: string; industry: string; market_cap: number; is_lq45: boolean; board: string }

// Screener
export interface ScreenerResult { symbol: string; name: string; sector: string; last_price: number; change_pct: number; volume: number; market_cap: number; pe_ratio: number | null; pbv_ratio: number | null; roe: number | null; dividend_yield: number | null; is_lq45: boolean }
export interface ScreenerResponse { meta: { total_matches: number; filters_applied: Record<string, unknown>; sort_by: string; limit: number }; results: ScreenerResult[] }

// Stock Detail
export interface StockProfile { symbol: string; name: string; exchange: string; sector: string; industry: string; listing_date: string; market_cap: number; last_price: number; shares_outstanding: number; is_lq45: boolean; description: string }
export interface FinancialSummary { symbol: string; period: string; revenue: number; net_income: number; total_assets: number; total_equity: number; eps: number; pe_ratio: number | null; pbv_ratio: number | null; roe: number | null; der: number | null }
export interface CorporateAction { symbol: string; action_type: string; ex_date: string; record_date: string; description: string; value: number | null }
export interface OwnershipEntry { holder_name: string; holder_type: string; shares_held: number; ownership_pct: number; change_from_prior: number | null }

// Trading
export interface OrderSubmitRequest { symbol: string; side: 'BUY' | 'SELL'; order_type: 'MARKET' | 'LIMIT'; quantity_lots: number; limit_price?: number; strategy_id?: string }
export interface OrderResponse { client_order_id: string; strategy_id: string | null; symbol: string; side: string; order_type: string; quantity: number; filled_quantity: number; limit_price: number | null; status: string; created_at: string }
export interface PositionResponse { symbol: string; exchange: string; strategy_id: string; quantity: number; avg_entry_price: number; current_price: number; unrealized_pnl: number; market_value: number; weight_pct: number }
export interface PnLResponse { date: string; total_equity: number; total_pnl: number; realized_pnl: number; unrealized_pnl: number; daily_return_pct: number }
export interface CircuitBreakerStatus { strategy_id: string; is_tripped: boolean; tripped_at: string | null; reason: string | null }

// Risk
export interface KillSwitchStatus { state: string; triggered_at: string | null; triggered_by: string | null; reason: string | null; open_orders_cancelled: number }
export interface RiskSnapshot { strategy_id: string; timestamp: string; nav_idr: number; exposure: { gross_exposure_idr: number; net_exposure_idr: number; long_exposure_idr: number; short_exposure_idr: number; beta_vs_ihsg: number }; concentration: { sector_hhi: number; top5_weight_pct: number; largest_position_pct: number; largest_position_symbol: string; num_positions: number }; var: { var_1d_95_idr: number; var_5d_95_idr: number; var_1d_99_idr: number; component_var: Record<string, number> }; daily_loss_pct: number; drawdown_pct: number; kill_switch_state: string }
export interface CapitalAllocation { strategy_id: string; strategy_name: string; allocated_idr: number; weight_pct: number; target_weight_pct: number; nav_idr: number }
export interface CapitalAllocationsResponse { total_capital_idr: number; total_allocated_idr: number; total_unallocated_idr: number; allocations: CapitalAllocation[] }

// Paper Trading
export interface PaperSession { id: string; name: string; strategy_id: string; status: string; mode: string; initial_capital_idr: number; current_nav_idr: number; peak_nav_idr: number; max_drawdown_pct: number; total_trades: number; winning_trades: number; realized_pnl_idr: number; total_commission_idr: number; cash_idr: number; unsettled_cash_idr: number; started_at: string | null; stopped_at: string | null; created_at: string }
export interface PaperSessionSummary { session_id: string; name: string; initial_capital_idr: number; final_nav_idr: number; total_return_pct: number; max_drawdown_pct: number; sharpe_ratio: number; sortino_ratio: number; calmar_ratio: number; total_trades: number; winning_trades: number; win_rate_pct: number; total_commission_idr: number; net_return_after_costs_pct: number; duration_days: number; started_at: string; stopped_at: string }
export interface PaperNavSnapshot { timestamp: string; nav_idr: number; cash_idr: number; gross_exposure_idr: number; drawdown_pct: number; daily_pnl_idr: number; daily_return_pct: number }

// Strategy
export interface Strategy { id: string; name: string; strategy_type: string; is_enabled: boolean; parameters: Record<string, unknown>; risk_limits: Record<string, unknown>; description: string; created_at: string; updated_at: string }
export interface StrategyPerformance { strategy_id: string; name: string; total_return_pct: number; sharpe_ratio: number; max_drawdown_pct: number; win_rate: number; total_trades: number; avg_holding_period_days: number; period_start: string; period_end: string }

// Backtest
export interface BacktestRequest { strategy_type: string; symbols: string[]; start_date: string; end_date: string; initial_capital?: number; slippage_bps?: number; strategy_params?: Record<string, unknown> }
export interface BacktestSubmission { task_id: string; status: string; submitted_at: string }
export interface BacktestResult { task_id: string; status: string; strategy_name: string; symbols: string[]; start_date: string; end_date: string; initial_capital: number; final_capital: number; completed_at: string | null; error_message: string | null }
export interface BacktestMetrics { task_id: string; total_return_pct: number; cagr_pct: number; sharpe_ratio: number; sortino_ratio: number; calmar_ratio: number; max_drawdown_pct: number; max_drawdown_duration_days: number; win_rate_pct: number; profit_factor: number; omega_ratio: number; total_trades: number; cost_drag_annualized_pct: number }

// News
export interface NewsArticle { id: string; title: string; source: string; url: string; published_at: string; summary: string; sentiment_score: number; sentiment_label: string; symbols: string[]; categories: string[] }
export interface SentimentSummary { symbol: string; article_count: number; avg_sentiment: number; sentiment_label: string; bullish_count: number; neutral_count: number; bearish_count: number; period_start: string; period_end: string }

// Macro
export interface MacroIndicator { code: string; name: string; latest_value: number; unit: string; period: string; source: string; updated_at: string }
export interface IndicatorDataPoint { period: string; value: number; date: string }
export interface YieldCurvePoint { tenor: string; yield_pct: number; change_bps: number }
export interface PolicyEvent { event_date: string; event_type: string; title: string; description: string; previous_value: number | null; consensus: number | null; actual: number | null }

// Commodities
export interface CommodityPrice { code: string; name: string; last_price: number; currency: string; unit: string; change_pct: number; change_1w_pct: number; change_1m_pct: number; updated_at: string }
export interface CommodityHistoryPoint { date: string; price: number; volume?: number }

// Fixed Income
export interface GovernmentBond { series: string; bond_type: string; coupon_rate: number; maturity_date: string; yield_to_maturity: number; price: number; duration: number; outstanding: number }
export interface CorporateBond { series: string; issuer: string; issuer_symbol: string; rating: string; coupon_rate: number; maturity_date: string; yield_to_maturity: number; price: number }
export interface CreditSpread { rating: string; tenor: string; spread_bps: number; change_bps: number; benchmark_yield: number }

// Governance
export interface GovernanceFlag { id: string; symbol: string; flag_type: string; severity: string; title: string; description: string; source: string; detected_at: string; resolved: boolean }
export interface OwnershipChange { symbol: string; holder_name: string; holder_type: string; change_type: string; shares_before: number; shares_after: number; change_pct: number; transaction_date: string; reported_date: string }
export interface AuditOpinion { symbol: string; fiscal_year: number; auditor: string; opinion: string; key_audit_matters: string[]; going_concern: boolean; report_date: string }

// Commodity Impact
export interface StockImpact { symbol: string; name: string; sector: string; correlation: number; beta: number; revenue_exposure_pct: number }
export interface CommodityImpactAnalysis { commodity_code: string; commodity_name: string; change_pct_30d: number; impacted_stocks: StockImpact[]; analysis_date: string }
export interface ImpactAlert { id: string; commodity_code: string; commodity_name: string; symbol: string; alert_type: string; severity: string; message: string; created_at: string }
export interface SensitivityCell { symbol: string; commodity_code: string; beta: number; correlation: number; r_squared: number }
export interface SensitivityMatrix { commodities: string[]; stocks: string[]; cells: SensitivityCell[]; computed_at: string }

// Promotion / Risk
export interface PromotionEvaluation { session_id: string; verdict: string; sharpe_ratio: number; sortino_ratio: number; max_drawdown_pct: number; trading_days: number; total_return_pct: number; win_rate_pct: number; notes: string[] }
export interface RiskHistoryPoint { timestamp: string; nav_idr: number; var_1d_95_idr: number; drawdown_pct: number; daily_loss_pct: number; gross_exposure_idr: number }
export interface RiskHistoryResponse { strategy_id: string; data_points: RiskHistoryPoint[] }
