export interface Strategy {
  id: string;
  name: string;
  description: string;
  type: 'momentum' | 'mean_reversion' | 'pairs_trading' | 'ml_signal' | 'statistical_arb' | 'custom';
  status: 'running' | 'paused' | 'stopped' | 'error' | 'deploying';
  mode: 'paper' | 'live';
  pnl: number;
  pnlPercent: number;
  dayPnl: number;
  sharpeRatio: number | null;
  maxDrawdown: number | null;
  tradesCount: number;
  winRate: number | null;
  avgHoldingPeriod: number | null;
  turnover: number | null;
  capitalAllocated: number;
  capitalUsed: number;
  lastTradeAt: string | null;
  errorMessage: string | null;
  parameters: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface StrategyFilters {
  type?: Strategy['type'];
  status?: Strategy['status'];
  mode?: Strategy['mode'];
}

export interface BacktestResult {
  id: string;
  strategyId: string;
  strategyName: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  finalEquity: number;
  totalReturn: number;
  cagr: number;
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  maxDrawdown: number;
  maxDrawdownDuration: number;
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  avgTradeDuration: number;
  turnover: number;
  commissionPaid: number;
  benchmarkReturn: number;
  alpha: number;
  beta: number;
  equityCurve: { timestamp: number; equity: number; drawdown: number; benchmark: number }[];
  monthlyReturns: { month: string; return: number; benchmark: number }[];
  completedAt: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  commission: number;
  tax: number;
  pnl: number | null;
  pnlPercent: number | null;
  holdingDays: number | null;
  signalConfidence: number | null;
  executedAt: string;
}
