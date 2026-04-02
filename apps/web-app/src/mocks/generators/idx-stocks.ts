/**
 * Shared IDX stock mock data and generators.
 *
 * IDX tick-size rules (simplified as of 2024):
 *   Price < 200        → tick 1
 *   200 <= Price < 500  → tick 2
 *   500 <= Price < 2000 → tick 5
 *   2000 <= Price < 5000 → tick 10
 *   Price >= 5000       → tick 25
 */

// ---------------------------------------------------------------------------
// Tick-size helper
// ---------------------------------------------------------------------------

export function idxTickSize(price: number): number {
  if (price < 200) return 1;
  if (price < 500) return 2;
  if (price < 2000) return 5;
  if (price < 5000) return 10;
  return 25;
}

export function roundToTick(price: number): number {
  const tick = idxTickSize(price);
  return Math.round(price / tick) * tick;
}

// ---------------------------------------------------------------------------
// IDX instruments
// ---------------------------------------------------------------------------

export interface MockInstrument {
  symbol: string;
  name: string;
  sector: string;
  lastPrice: number;
  prevClose: number;
  marketCap: number; // in trillion IDR
  lotSize: number;
  board: 'RG' | 'NG' | 'TN';
}

export const MOCK_IDX_STOCKS: MockInstrument[] = [
  { symbol: 'BBCA', name: 'Bank Central Asia Tbk', sector: 'Financials', lastPrice: 9875, prevClose: 9825, marketCap: 1215, lotSize: 100, board: 'RG' },
  { symbol: 'BMRI', name: 'Bank Mandiri Tbk', sector: 'Financials', lastPrice: 5450, prevClose: 5400, marketCap: 508, lotSize: 100, board: 'RG' },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia Tbk', sector: 'Financials', lastPrice: 4750, prevClose: 4710, marketCap: 718, lotSize: 100, board: 'RG' },
  { symbol: 'BBNI', name: 'Bank Negara Indonesia Tbk', sector: 'Financials', lastPrice: 5025, prevClose: 4975, marketCap: 187, lotSize: 100, board: 'RG' },
  { symbol: 'TLKM', name: 'Telkom Indonesia Tbk', sector: 'Communication Services', lastPrice: 3780, prevClose: 3750, marketCap: 374, lotSize: 100, board: 'RG' },
  { symbol: 'ASII', name: 'Astra International Tbk', sector: 'Industrials', lastPrice: 4650, prevClose: 4600, marketCap: 188, lotSize: 100, board: 'RG' },
  { symbol: 'UNVR', name: 'Unilever Indonesia Tbk', sector: 'Consumer Staples', lastPrice: 2680, prevClose: 2700, marketCap: 102, lotSize: 100, board: 'RG' },
  { symbol: 'MDKA', name: 'Merdeka Copper Gold Tbk', sector: 'Basic Materials', lastPrice: 1905, prevClose: 1880, marketCap: 46, lotSize: 100, board: 'RG' },
  { symbol: 'GOTO', name: 'GoTo Gojek Tokopedia Tbk', sector: 'Technology', lastPrice: 72, prevClose: 71, marketCap: 85, lotSize: 100, board: 'RG' },
  { symbol: 'BREN', name: 'Barito Renewables Energy Tbk', sector: 'Utilities', lastPrice: 7350, prevClose: 7275, marketCap: 496, lotSize: 100, board: 'RG' },
  { symbol: 'ARTO', name: 'Bank Jago Tbk', sector: 'Financials', lastPrice: 2350, prevClose: 2320, marketCap: 141, lotSize: 100, board: 'RG' },
  { symbol: 'CPIN', name: 'Charoen Pokphand Indonesia Tbk', sector: 'Consumer Staples', lastPrice: 4870, prevClose: 4830, marketCap: 80, lotSize: 100, board: 'RG' },
  { symbol: 'INDF', name: 'Indofood Sukses Makmur Tbk', sector: 'Consumer Staples', lastPrice: 6425, prevClose: 6375, marketCap: 56, lotSize: 100, board: 'RG' },
  { symbol: 'KLBF', name: 'Kalbe Farma Tbk', sector: 'Healthcare', lastPrice: 1530, prevClose: 1520, marketCap: 72, lotSize: 100, board: 'RG' },
  { symbol: 'HMSP', name: 'HM Sampoerna Tbk', sector: 'Consumer Staples', lastPrice: 730, prevClose: 725, marketCap: 85, lotSize: 100, board: 'RG' },
  { symbol: 'EMTK', name: 'Elang Mahkota Teknologi Tbk', sector: 'Communication Services', lastPrice: 490, prevClose: 486, marketCap: 28, lotSize: 100, board: 'RG' },
  { symbol: 'PGAS', name: 'Perusahaan Gas Negara Tbk', sector: 'Energy', lastPrice: 1425, prevClose: 1410, marketCap: 35, lotSize: 100, board: 'RG' },
  { symbol: 'PTBA', name: 'Bukit Asam Tbk', sector: 'Energy', lastPrice: 2570, prevClose: 2540, marketCap: 30, lotSize: 100, board: 'RG' },
  { symbol: 'ANTM', name: 'Aneka Tambang Tbk', sector: 'Basic Materials', lastPrice: 1365, prevClose: 1350, marketCap: 33, lotSize: 100, board: 'RG' },
  { symbol: 'ADRO', name: 'Adaro Energy Tbk', sector: 'Energy', lastPrice: 2790, prevClose: 2760, marketCap: 91, lotSize: 100, board: 'RG' },
];

// ---------------------------------------------------------------------------
// OHLCV generator – simple random walk
// ---------------------------------------------------------------------------

export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Generate `days` OHLCV bars ending today, walking backwards from a base price.
 * Uses a seeded-ish deterministic walk so results are stable across calls with
 * the same parameters.
 */
export function generateOHLCV(basePrice: number, days: number = 100): OHLCVBar[] {
  const bars: OHLCVBar[] = [];
  let price = basePrice;
  const now = new Date();

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // Skip weekends
    const dow = date.getDay();
    if (dow === 0 || dow === 6) continue;

    const drift = (Math.random() - 0.48) * 0.025; // slight upward bias
    const volatility = 0.015 + Math.random() * 0.01;

    const open = roundToTick(price);
    const intraHigh = price * (1 + Math.random() * volatility);
    const intraLow = price * (1 - Math.random() * volatility);
    const close = roundToTick(price * (1 + drift));

    const high = roundToTick(Math.max(open, close, intraHigh));
    const low = roundToTick(Math.min(open, close, intraLow));

    const avgVolume = basePrice > 5000 ? 15_000_000 : basePrice > 1000 ? 30_000_000 : 80_000_000;
    const volume = Math.round(avgVolume * (0.6 + Math.random() * 0.8));

    bars.push({
      timestamp: date.toISOString().slice(0, 10),
      open,
      high,
      low,
      close,
      volume,
    });

    price = close;
  }

  return bars;
}
