import { roundToTick, idxTickSize } from './idx-stocks';

export interface OrderbookLevel {
  price: number;
  volume: number;
  total: number;
}

export interface OrderbookSnapshot {
  symbol: string;
  timestamp: string;
  asks: OrderbookLevel[];
  bids: OrderbookLevel[];
}

const BASE_PRICES: Record<string, number> = {
  BBCA: 4000,
  BBRI: 5500,
  BMRI: 3000,
  TLKM: 3780,
  ASII: 4650,
};

function seeded(seed: number) {
  let s = seed || 1;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function symbolSeed(symbol: string, timeBucket: number): number {
  let h = timeBucket;
  for (let i = 0; i < symbol.length; i++) {
    h = (h * 31 + symbol.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function generateOrderbook(symbol: string, levels = 10): OrderbookSnapshot {
  const upper = symbol.toUpperCase();
  const base = BASE_PRICES[upper] ?? 4000;

  // Refresh every 5s so router.refresh() surfaces new data
  const bucket = Math.floor(Date.now() / 5000);
  const rand = seeded(symbolSeed(upper, bucket));

  const tick = idxTickSize(base);
  const halfSpreadPct = 0.0025 + rand() * 0.005; // 0.25%–0.75%
  const spread = Math.max(tick, roundToTick(base * halfSpreadPct));

  const bestAsk = roundToTick(base + spread / 2);
  const bestBid = roundToTick(base - spread / 2);

  const asks: OrderbookLevel[] = [];
  const bids: OrderbookLevel[] = [];

  let askTotal = 0;
  for (let i = 0; i < levels; i++) {
    const price = bestAsk + idxTickSize(bestAsk + i * tick) * i;
    const volume = Math.round(10 + rand() * 490);
    askTotal += volume;
    asks.push({ price, volume, total: askTotal });
  }

  let bidTotal = 0;
  for (let i = 0; i < levels; i++) {
    const price = bestBid - idxTickSize(bestBid - i * tick) * i;
    const volume = Math.round(10 + rand() * 490);
    bidTotal += volume;
    bids.push({ price, volume, total: bidTotal });
  }

  return {
    symbol: upper,
    timestamp: new Date(bucket * 5000).toISOString(),
    asks,
    bids,
  };
}
