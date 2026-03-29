import api from './client';
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserProfile,
  MarketOverview,
  OHLCVBar,
  Instrument,
  ScreenerResponse,
  StockProfile,
  FinancialSummary,
  CorporateAction,
  OwnershipEntry,
  OrderSubmitRequest,
  OrderResponse,
  PositionResponse,
  PnLResponse,
  CircuitBreakerStatus,
  KillSwitchStatus,
  RiskSnapshot,
  CapitalAllocationsResponse,
  PaperSession,
  PaperSessionSummary,
  PaperNavSnapshot,
  Strategy,
  StrategyPerformance,
  BacktestRequest,
  BacktestSubmission,
  BacktestResult,
  BacktestMetrics,
  NewsArticle,
  SentimentSummary,
  MacroIndicator,
  IndicatorDataPoint,
  YieldCurvePoint,
  PolicyEvent,
  CommodityPrice,
  CommodityHistoryPoint,
  GovernmentBond,
  CorporateBond,
  CreditSpread,
  CommodityImpactAnalysis,
  ImpactAlert,
  SensitivityMatrix,
  GovernanceFlag,
  OwnershipChange,
  AuditOpinion,
  PromotionEvaluation,
  RiskHistoryResponse,
} from '../types';

// Auth
export const authApi = {
  login: (data: LoginRequest) =>
    api.post<TokenResponse>('/v1/auth/login', data),
  register: (data: RegisterRequest) =>
    api.post<UserProfile>('/v1/auth/register', data),
  refresh: (token: string) =>
    api.post<TokenResponse>('/v1/auth/refresh', { refresh_token: token }),
  me: () =>
    api.get<UserProfile>('/v1/auth/me'),
};

// Market
export const marketApi = {
  overview: () =>
    api.get<MarketOverview>('/v1/market/overview'),
  ohlcv: (symbol: string, params?: { interval?: string; start?: string; end?: string; limit?: number }) =>
    api.get<OHLCVBar[]>(`/v1/market/ohlcv/${symbol}`, { params }),
  instruments: (params?: { exchange?: string; sector?: string; lq45_only?: boolean; board?: string }) =>
    api.get<Instrument[]>('/v1/market/instruments', { params }),
  instrument: (symbol: string) =>
    api.get<Instrument>(`/v1/market/instruments/${symbol}`),
};

// Screener
export const screenerApi = {
  screen: (params?: {
    sector?: string;
    min_market_cap?: number;
    max_market_cap?: number;
    min_pe?: number;
    max_pe?: number;
    min_pbv?: number;
    max_pbv?: number;
    min_roe?: number;
    max_roe?: number;
    min_dividend_yield?: number;
    lq45_only?: boolean;
    sort_by?: string;
    sort_dir?: string;
    limit?: number;
    offset?: number;
  }) =>
    api.get<ScreenerResponse>('/v1/screener', { params }),
};

// Stock
export const stockApi = {
  profile: (symbol: string) =>
    api.get<StockProfile>(`/v1/stocks/${symbol}/profile`),
  financials: (symbol: string, params?: { period?: string; limit?: number }) =>
    api.get<FinancialSummary[]>(`/v1/stocks/${symbol}/financials`, { params }),
  corporateActions: (symbol: string, params?: { action_type?: string; limit?: number }) =>
    api.get<CorporateAction[]>(`/v1/stocks/${symbol}/corporate-actions`, { params }),
  ownership: (symbol: string) =>
    api.get<OwnershipEntry[]>(`/v1/stocks/${symbol}/ownership`),
};

// Trading
export const tradingApi = {
  submitOrder: (data: OrderSubmitRequest) =>
    api.post<OrderResponse>('/v1/trading/orders', data),
  getOrders: (params?: { status?: string; symbol?: string; strategy_id?: string; limit?: number }) =>
    api.get<OrderResponse[]>('/v1/trading/orders', { params }),
  getOrder: (orderId: string) =>
    api.get<OrderResponse>(`/v1/trading/orders/${orderId}`),
  cancelOrder: (orderId: string) =>
    api.delete<OrderResponse>(`/v1/trading/orders/${orderId}`),
  positions: (params?: { strategy_id?: string }) =>
    api.get<PositionResponse[]>('/v1/trading/positions', { params }),
  pnl: (params?: { start_date?: string; end_date?: string; strategy_id?: string }) =>
    api.get<PnLResponse[]>('/v1/trading/pnl', { params }),
  circuitBreakers: () =>
    api.get<CircuitBreakerStatus[]>('/v1/trading/circuit-breakers'),
  resetCircuitBreaker: (strategyId: string) =>
    api.post<CircuitBreakerStatus>(`/v1/trading/circuit-breakers/${strategyId}/reset`),
};

// Risk
export const riskApi = {
  killSwitch: () =>
    api.get<KillSwitchStatus>('/v1/risk/kill-switch'),
  activateKillSwitch: (reason: string) =>
    api.post<KillSwitchStatus>('/v1/risk/kill-switch/activate', { reason }),
  deactivateKillSwitch: () =>
    api.post<KillSwitchStatus>('/v1/risk/kill-switch/deactivate'),
  snapshot: (strategyId: string) =>
    api.get<RiskSnapshot>(`/v1/risk/snapshot/${strategyId}`),
  capitalAllocations: () =>
    api.get<CapitalAllocationsResponse>('/v1/risk/capital-allocations'),
  updateCapitalAllocation: (strategyId: string, data: { allocated_idr: number; target_weight_pct: number }) =>
    api.put<void>(`/v1/risk/capital-allocations/${strategyId}`, data),
  history: (strategyId: string, params?: { start?: string; end?: string; limit?: number }) =>
    api.get<RiskHistoryResponse>(`/v1/risk/history/${strategyId}`, { params }),
};

// Paper Trading
export const paperTradingApi = {
  listSessions: (params?: { status?: string; strategy_id?: string }) =>
    api.get<PaperSession[]>('/v1/paper-trading/sessions', { params }),
  createSession: (data: { name: string; strategy_id: string; initial_capital_idr: number; mode?: string }) =>
    api.post<PaperSession>('/v1/paper-trading/sessions', data),
  getSession: (sessionId: string) =>
    api.get<PaperSession>(`/v1/paper-trading/sessions/${sessionId}`),
  startSession: (sessionId: string) =>
    api.post<PaperSession>(`/v1/paper-trading/sessions/${sessionId}/start`),
  stopSession: (sessionId: string) =>
    api.post<PaperSession>(`/v1/paper-trading/sessions/${sessionId}/stop`),
  deleteSession: (sessionId: string) =>
    api.delete<void>(`/v1/paper-trading/sessions/${sessionId}`),
  sessionSummary: (sessionId: string) =>
    api.get<PaperSessionSummary>(`/v1/paper-trading/sessions/${sessionId}/summary`),
  sessionNav: (sessionId: string, params?: { start?: string; end?: string; limit?: number }) =>
    api.get<PaperNavSnapshot[]>(`/v1/paper-trading/sessions/${sessionId}/nav`, { params }),
  sessionPositions: (sessionId: string) =>
    api.get<PositionResponse[]>(`/v1/paper-trading/sessions/${sessionId}/positions`),
  sessionOrders: (sessionId: string, params?: { status?: string; limit?: number }) =>
    api.get<OrderResponse[]>(`/v1/paper-trading/sessions/${sessionId}/orders`, { params }),
  promotionEvaluation: (sessionId: string) =>
    api.get<PromotionEvaluation>(`/v1/paper-trading/sessions/${sessionId}/promotion-evaluation`),
};

// Strategy
export const strategyApi = {
  list: () =>
    api.get<Strategy[]>('/v1/strategies'),
  get: (strategyId: string) =>
    api.get<Strategy>(`/v1/strategies/${strategyId}`),
  create: (data: { name: string; strategy_type: string; parameters?: Record<string, unknown>; risk_limits?: Record<string, unknown>; description?: string }) =>
    api.post<Strategy>('/v1/strategies', data),
  update: (strategyId: string, data: { name?: string; is_enabled?: boolean; parameters?: Record<string, unknown>; risk_limits?: Record<string, unknown>; description?: string }) =>
    api.put<Strategy>(`/v1/strategies/${strategyId}`, data),
  delete: (strategyId: string) =>
    api.delete<void>(`/v1/strategies/${strategyId}`),
  performance: (strategyId: string, params?: { start?: string; end?: string }) =>
    api.get<StrategyPerformance>(`/v1/strategies/${strategyId}/performance`, { params }),
};

// Backtest
export const backtestApi = {
  submit: (data: BacktestRequest) =>
    api.post<BacktestSubmission>('/v1/backtests', data),
  list: (params?: { status?: string; limit?: number }) =>
    api.get<BacktestResult[]>('/v1/backtests', { params }),
  get: (taskId: string) =>
    api.get<BacktestResult>(`/v1/backtests/${taskId}`),
  metrics: (taskId: string) =>
    api.get<BacktestMetrics>(`/v1/backtests/${taskId}/metrics`),
  equityCurve: (taskId: string) =>
    api.get<{ timestamp: string; equity: number }[]>(`/v1/backtests/${taskId}/equity-curve`),
  delete: (taskId: string) =>
    api.delete<void>(`/v1/backtests/${taskId}`),
};

// News
export const newsApi = {
  list: (params?: { symbol?: string; category?: string; sentiment?: string; start?: string; end?: string; limit?: number; offset?: number }) =>
    api.get<NewsArticle[]>('/v1/news', { params }),
  get: (articleId: string) =>
    api.get<NewsArticle>(`/v1/news/${articleId}`),
  sentiment: (symbol: string, params?: { start?: string; end?: string }) =>
    api.get<SentimentSummary>(`/v1/news/sentiment/${symbol}`, { params }),
};

// Macro
export const macroApi = {
  indicators: () =>
    api.get<MacroIndicator[]>('/v1/macro/indicators'),
  indicator: (code: string) =>
    api.get<MacroIndicator>(`/v1/macro/indicators/${code}`),
  indicatorHistory: (code: string, params?: { start?: string; end?: string; limit?: number }) =>
    api.get<IndicatorDataPoint[]>(`/v1/macro/indicators/${code}/history`, { params }),
  yieldCurve: () =>
    api.get<YieldCurvePoint[]>('/v1/macro/yield-curve'),
  policyEvents: (params?: { start?: string; end?: string; event_type?: string; limit?: number }) =>
    api.get<PolicyEvent[]>('/v1/macro/policy-events', { params }),
};

// Commodities
export const commodityApi = {
  prices: (params?: { category?: string }) =>
    api.get<CommodityPrice[]>('/v1/commodities/prices', { params }),
  price: (code: string) =>
    api.get<CommodityPrice>(`/v1/commodities/prices/${code}`),
  history: (code: string, params?: { start?: string; end?: string; limit?: number }) =>
    api.get<CommodityHistoryPoint[]>(`/v1/commodities/prices/${code}/history`, { params }),
};

// Fixed Income
export const fixedIncomeApi = {
  governmentBonds: (params?: { bond_type?: string; min_tenor?: number; max_tenor?: number }) =>
    api.get<GovernmentBond[]>('/v1/fixed-income/government-bonds', { params }),
  governmentBond: (series: string) =>
    api.get<GovernmentBond>(`/v1/fixed-income/government-bonds/${series}`),
  corporateBonds: (params?: { rating?: string; issuer_symbol?: string; limit?: number }) =>
    api.get<CorporateBond[]>('/v1/fixed-income/corporate-bonds', { params }),
  corporateBond: (series: string) =>
    api.get<CorporateBond>(`/v1/fixed-income/corporate-bonds/${series}`),
  creditSpreads: (params?: { rating?: string }) =>
    api.get<CreditSpread[]>('/v1/fixed-income/credit-spreads', { params }),
};

// Commodity Impact
export const commodityImpactApi = {
  analysis: (commodityCode: string) =>
    api.get<CommodityImpactAnalysis>(`/v1/commodity-impact/analysis/${commodityCode}`),
  alerts: (params?: { commodity_code?: string; symbol?: string; severity?: string; limit?: number }) =>
    api.get<ImpactAlert[]>('/v1/commodity-impact/alerts', { params }),
  sensitivityMatrix: (params?: { commodities?: string; stocks?: string }) =>
    api.get<SensitivityMatrix>('/v1/commodity-impact/sensitivity-matrix', { params }),
};

// Governance
export const governanceApi = {
  flags: (params?: { symbol?: string; flag_type?: string; severity?: string; resolved?: boolean; limit?: number }) =>
    api.get<GovernanceFlag[]>('/v1/governance/flags', { params }),
  flag: (flagId: string) =>
    api.get<GovernanceFlag>(`/v1/governance/flags/${flagId}`),
  ownershipChanges: (symbol: string, params?: { start?: string; end?: string; limit?: number }) =>
    api.get<OwnershipChange[]>(`/v1/governance/ownership-changes/${symbol}`, { params }),
  auditOpinions: (symbol: string, params?: { limit?: number }) =>
    api.get<AuditOpinion[]>(`/v1/governance/audit-opinions/${symbol}`, { params }),
};
