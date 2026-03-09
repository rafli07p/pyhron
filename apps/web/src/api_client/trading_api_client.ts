import axios from 'axios';

const api = axios.create({ baseURL: '/api/v1' });

export interface Strategy {
  id: string;
  name: string;
  strategyType: string;
  isEnabled: boolean;
  parameters: Record<string, unknown>;
}

export interface Position {
  symbol: string;
  strategyId: string;
  quantity: number;
  avgEntryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  marketValue: number;
}

export interface Order {
  clientOrderId: string;
  strategyId: string;
  symbol: string;
  side: string;
  orderType: string;
  quantity: number;
  status: string;
  createdAt: string;
}

export interface BacktestResult {
  taskId: string;
  status: string;
  metrics?: {
    totalReturn: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winRate: number;
  };
}

export const tradingApi = {
  getStrategies: () =>
    api.get<Strategy[]>('/strategies'),

  createStrategy: (data: { name: string; strategyType: string; parameters: Record<string, unknown> }) =>
    api.post<Strategy>('/strategies', data),

  enableStrategy: (id: string) =>
    api.post(`/strategies/${id}/enable`),

  disableStrategy: (id: string) =>
    api.post(`/strategies/${id}/disable`),

  getPositions: (params?: { strategyId?: string }) =>
    api.get<Position[]>('/trading/positions', { params }),

  getOrders: (params?: { strategyId?: string; status?: string; limit?: number }) =>
    api.get<Order[]>('/trading/orders', { params }),

  runBacktest: (data: { strategyId: string; symbols: string[]; startDate: string; endDate: string }) =>
    api.post<BacktestResult>('/backtest/run', data),

  getBacktestResult: (taskId: string) =>
    api.get<BacktestResult>(`/backtest/${taskId}`),
};
