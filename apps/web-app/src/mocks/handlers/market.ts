import { http, HttpResponse } from 'msw';
import { MOCK_IDX_STOCKS, generateOHLCV } from '../generators/idx-stocks';
import { generateOrderbook } from '../generators/orderbook';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Base prices for OHLCV generation keyed by symbol
const BASE_PRICES: Record<string, number> = {
  BBCA: 9875,
  BMRI: 5450,
  TLKM: 3780,
  ASII: 4650,
};

// Fill from MOCK_IDX_STOCKS for any symbol not explicitly listed
for (const s of MOCK_IDX_STOCKS) {
  if (!BASE_PRICES[s.symbol]) {
    BASE_PRICES[s.symbol] = s.lastPrice;
  }
}

export const marketHandlers = [
  // -----------------------------------------------------------------------
  // Market overview
  // -----------------------------------------------------------------------
  http.get(`${API_BASE}/v1/markets/overview`, () => {
    return HttpResponse.json({
      index: 'IHSG',
      value: 7234.56,
      change: 32.45,
      change_pct: 0.45,
      advances: 312,
      declines: 198,
      unchanged: 142,
      volume: 12_450_000_000,
      value_traded: 8_730_000_000_000,
      updated_at: new Date().toISOString(),
    });
  }),

  // -----------------------------------------------------------------------
  // OHLCV for a symbol
  // -----------------------------------------------------------------------
  http.get(`${API_BASE}/v1/markets/ohlcv/:symbol`, ({ params }) => {
    const symbol = (params.symbol as string).toUpperCase();
    const base = BASE_PRICES[symbol];
    if (!base) {
      return HttpResponse.json({ detail: `Unknown symbol: ${symbol}` }, { status: 404 });
    }
    return HttpResponse.json({
      symbol,
      interval: '1d',
      bars: generateOHLCV(base, 100),
    });
  }),

  // -----------------------------------------------------------------------
  // Instruments list (first 10)
  // -----------------------------------------------------------------------
  http.get(`${API_BASE}/v1/markets/instruments`, () => {
    const instruments = MOCK_IDX_STOCKS.slice(0, 10).map((s) => ({
      symbol: s.symbol,
      name: s.name,
      sector: s.sector,
      last_price: s.lastPrice,
      prev_close: s.prevClose,
      change: s.lastPrice - s.prevClose,
      change_pct: Number((((s.lastPrice - s.prevClose) / s.prevClose) * 100).toFixed(2)),
      market_cap_trillion: s.marketCap,
      lot_size: s.lotSize,
      board: s.board,
    }));
    return HttpResponse.json({ instruments, total: instruments.length });
  }),

  // -----------------------------------------------------------------------
  // Orderbook snapshot for a symbol
  // -----------------------------------------------------------------------
  http.get(`${API_BASE}/v1/markets/orderbook/:symbol`, ({ params }) => {
    const symbol = (params.symbol as string).toUpperCase();
    return HttpResponse.json(generateOrderbook(symbol));
  }),

  // -----------------------------------------------------------------------
  // Single instrument detail
  // -----------------------------------------------------------------------
  http.get(`${API_BASE}/v1/markets/instruments/:symbol`, ({ params }) => {
    const symbol = (params.symbol as string).toUpperCase();
    const stock = MOCK_IDX_STOCKS.find((s) => s.symbol === symbol);
    if (!stock) {
      return HttpResponse.json({ detail: `Instrument not found: ${symbol}` }, { status: 404 });
    }
    return HttpResponse.json({
      symbol: stock.symbol,
      name: stock.name,
      sector: stock.sector,
      last_price: stock.lastPrice,
      prev_close: stock.prevClose,
      change: stock.lastPrice - stock.prevClose,
      change_pct: Number((((stock.lastPrice - stock.prevClose) / stock.prevClose) * 100).toFixed(2)),
      market_cap_trillion: stock.marketCap,
      lot_size: stock.lotSize,
      board: stock.board,
      open: stock.lastPrice - Math.round(Math.random() * 50),
      high: stock.lastPrice + Math.round(Math.random() * 75),
      low: stock.lastPrice - Math.round(Math.random() * 75),
      volume: Math.round(15_000_000 + Math.random() * 20_000_000),
      foreign_buy: Math.round(2_000_000 + Math.random() * 5_000_000),
      foreign_sell: Math.round(1_500_000 + Math.random() * 4_000_000),
    });
  }),
];
