import type { ScreenerFilters } from '@/types/market';
import type { StrategyFilters } from '@/types/strategy';
import type { SignalFilters } from '@/types/signal';

interface OrderFilters {
  status?: string;
  symbol?: string;
  page?: number;
}

interface TradeHistoryFilters {
  symbol?: string;
  startDate?: string;
  endDate?: string;
  cursor?: string;
}

export const queryKeys = {
  portfolio: {
    all: ['portfolio'] as const,
    positions: () => [...queryKeys.portfolio.all, 'positions'] as const,
    orders: (filters?: OrderFilters) => [...queryKeys.portfolio.all, 'orders', filters] as const,
    performance: (period: string) => [...queryKeys.portfolio.all, 'performance', period] as const,
    risk: () => [...queryKeys.portfolio.all, 'risk'] as const,
    history: (filters?: TradeHistoryFilters) =>
      [...queryKeys.portfolio.all, 'history', filters] as const,
  },
  markets: {
    all: ['markets'] as const,
    overview: () => [...queryKeys.markets.all, 'overview'] as const,
    instrument: (symbol: string) => [...queryKeys.markets.all, 'instrument', symbol] as const,
    ohlcv: (symbol: string, tf: string, range: string) =>
      [...queryKeys.markets.all, 'ohlcv', symbol, tf, range] as const,
    screener: (filters: ScreenerFilters) => [...queryKeys.markets.all, 'screener', filters] as const,
    watchlists: () => [...queryKeys.markets.all, 'watchlists'] as const,
    watchlist: (id: string) => [...queryKeys.markets.all, 'watchlist', id] as const,
    calendar: (month: string) => [...queryKeys.markets.all, 'calendar', month] as const,
  },
  strategies: {
    all: ['strategies'] as const,
    list: (filters?: StrategyFilters) => [...queryKeys.strategies.all, 'list', filters] as const,
    detail: (id: string) => [...queryKeys.strategies.all, id] as const,
    logs: (id: string) => [...queryKeys.strategies.all, id, 'logs'] as const,
    backtests: (strategyId?: string) =>
      [...queryKeys.strategies.all, 'backtests', strategyId] as const,
    backtest: (id: string) => [...queryKeys.strategies.all, 'backtest', id] as const,
  },
  research: {
    all: ['research'] as const,
    signals: (filters?: SignalFilters) => [...queryKeys.research.all, 'signals', filters] as const,
    articles: (page: number, tag?: string) =>
      [...queryKeys.research.all, 'articles', page, tag] as const,
    article: (slug: string) => [...queryKeys.research.all, 'article', slug] as const,
    factors: () => [...queryKeys.research.all, 'factors'] as const,
  },
  ml: {
    all: ['ml'] as const,
    experiments: () => [...queryKeys.ml.all, 'experiments'] as const,
    models: () => [...queryKeys.ml.all, 'models'] as const,
    model: (id: string) => [...queryKeys.ml.all, 'model', id] as const,
  },
  user: {
    all: ['user'] as const,
    profile: () => [...queryKeys.user.all, 'profile'] as const,
    notifications: () => [...queryKeys.user.all, 'notifications'] as const,
    apiKeys: () => [...queryKeys.user.all, 'api-keys'] as const,
    preferences: () => [...queryKeys.user.all, 'preferences'] as const,
  },
} as const;
