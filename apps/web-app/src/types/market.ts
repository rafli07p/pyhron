export interface Instrument {
  symbol: string;
  name: string;
  sector: string;
  subSector: string;
  board: 'regular' | 'development' | 'acceleration';
  marketCap: number;
  lastPrice: number;
  change: number;
  changePercent: number;
  volume: number;
  value: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
  bid: number;
  ask: number;
  bidVolume: number;
  askVolume: number;
  week52High: number;
  week52Low: number;
  avgVolume20: number;
  sharesOutstanding: number;
  freeFloat: number | null;
  pe: number | null;
  pb: number | null;
  eps: number | null;
  roe: number | null;
  dividendYield: number | null;
  beta: number | null;
  updatedAt: string;
}

export interface OHLCV {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OrderBookLevel {
  price: number;
  volume: number;
  orders: number;
}

export interface OrderBook {
  symbol: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: number;
}

export interface ScreenerFilters {
  sector?: string;
  minMarketCap?: number;
  maxMarketCap?: number;
  minPE?: number;
  maxPE?: number;
  minDividendYield?: number;
  minVolume?: number;
  board?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}
