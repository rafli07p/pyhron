export interface Position {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  side: 'long';
  quantity: number;
  lots: number;
  avgPrice: number;
  currentPrice: number;
  previousClose: number;
  marketValue: number;
  costBasis: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  dayPnl: number;
  dayPnlPercent: number;
  weight: number;
  beta: number | null;
  updatedAt: string;
}

export interface Order {
  id: string;
  clientOrderId: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop' | 'stop_limit';
  status: 'pending' | 'new' | 'partially_filled' | 'filled' | 'cancelled' | 'rejected' | 'expired';
  quantity: number;
  filledQuantity: number;
  remainingQuantity: number;
  price: number | null;
  stopPrice: number | null;
  avgFillPrice: number | null;
  commission: number;
  tax: number;
  timeInForce: 'day' | 'gtc' | 'ioc' | 'fok';
  strategyId: string | null;
  strategyName: string | null;
  createdAt: string;
  updatedAt: string;
  filledAt: string | null;
  rejectionReason: string | null;
}

export type OrderInput = {
  symbol: string;
  side: 'buy' | 'sell';
  type: Order['type'];
  quantity: number;
  price?: number;
  stopPrice?: number;
  timeInForce?: Order['timeInForce'];
};
