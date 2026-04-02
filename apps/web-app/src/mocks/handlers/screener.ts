import { http, HttpResponse } from 'msw';
import { MOCK_IDX_STOCKS, roundToTick } from '../generators/idx-stocks';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function generateScreenerData() {
  return MOCK_IDX_STOCKS.map((stock) => {
    const change = stock.lastPrice - stock.prevClose;
    const changePct = ((change / stock.prevClose) * 100);
    const pe = 8 + Math.random() * 30;
    const pb = 0.5 + Math.random() * 5;
    const roe = 5 + Math.random() * 25;
    const debtToEquity = 0.1 + Math.random() * 2.5;
    const divYield = Math.random() * 6;
    const rsi14 = 25 + Math.random() * 50;
    const avgVolume20d = stock.lastPrice > 5000
      ? 10_000_000 + Math.random() * 15_000_000
      : stock.lastPrice > 1000
        ? 20_000_000 + Math.random() * 30_000_000
        : 50_000_000 + Math.random() * 80_000_000;

    return {
      symbol: stock.symbol,
      name: stock.name,
      sector: stock.sector,
      last_price: stock.lastPrice,
      prev_close: stock.prevClose,
      change,
      change_pct: Number(changePct.toFixed(2)),
      market_cap_trillion: stock.marketCap,
      volume: Math.round(avgVolume20d * (0.7 + Math.random() * 0.6)),
      avg_volume_20d: Math.round(avgVolume20d),
      pe_ratio: Number(pe.toFixed(2)),
      pb_ratio: Number(pb.toFixed(2)),
      roe_pct: Number(roe.toFixed(2)),
      debt_to_equity: Number(debtToEquity.toFixed(2)),
      dividend_yield_pct: Number(divYield.toFixed(2)),
      rsi_14: Number(rsi14.toFixed(1)),
      sma_20: roundToTick(stock.lastPrice * (0.97 + Math.random() * 0.06)),
      sma_50: roundToTick(stock.lastPrice * (0.94 + Math.random() * 0.12)),
      sma_200: roundToTick(stock.lastPrice * (0.88 + Math.random() * 0.24)),
      high_52w: roundToTick(stock.lastPrice * (1.05 + Math.random() * 0.25)),
      low_52w: roundToTick(stock.lastPrice * (0.6 + Math.random() * 0.25)),
      foreign_net_buy: Math.round((Math.random() - 0.4) * 10_000_000),
      board: stock.board,
      lot_size: stock.lotSize,
    };
  });
}

export const screenerHandlers = [
  http.get(`${API_BASE}/v1/screener/screen`, () => {
    const results = generateScreenerData();
    return HttpResponse.json({
      results,
      total: results.length,
      filters_applied: [],
      sorted_by: 'market_cap_trillion',
      sort_order: 'desc',
      generated_at: new Date().toISOString(),
    });
  }),
];
