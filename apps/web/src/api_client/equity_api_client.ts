import axios from 'axios';

const api = axios.create({ baseURL: '/api/v1' });

export interface Instrument {
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  marketCap: number | null;
  isLq45: boolean;
}

export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ScreenerResult {
  symbol: string;
  name: string;
  lastPrice: number;
  changePct: number;
  volume: number;
  marketCap: number | null;
  sector: string | null;
}

export const equityApi = {
  getInstruments: (params?: { sector?: string; lq45Only?: boolean }) =>
    api.get<Instrument[]>('/market/instruments', { params }),

  getInstrument: (symbol: string) =>
    api.get<Instrument>(`/market/instruments/${symbol}`),

  getOHLCV: (symbol: string, params?: { interval?: string; limit?: number }) =>
    api.get<OHLCVBar[]>(`/market/ohlcv/${symbol}`, { params }),

  screenStocks: (params?: { sector?: string; minVolume?: number; sortBy?: string }) =>
    api.get<ScreenerResult[]>('/screener/screen', { params }),

  getStockDetail: (symbol: string) =>
    api.get(`/stocks/${symbol}`),

  getFinancials: (symbol: string) =>
    api.get(`/stocks/${symbol}/financials`),

  getNews: (params?: { symbol?: string; limit?: number }) =>
    api.get('/news', { params }),
};
