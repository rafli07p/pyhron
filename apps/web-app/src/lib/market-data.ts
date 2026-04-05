import YahooFinance from 'yahoo-finance2';
import {
  INDICES,
  POSITIONS,
  generateOHLCV,
  generateScreenerData,
  getInstrumentDetail,
} from '@/mocks/terminal-data';

const yahooFinance = new YahooFinance();

// ─── Helpers ──────────────────────────────────────────────

/** Append `.JK` suffix for IDX tickers on Yahoo Finance */
export function toYahooSymbol(symbol: string): string {
  if (symbol.startsWith('^')) return symbol;
  return symbol.endsWith('.JK') ? symbol : `${symbol}.JK`;
}

// ─── Types ────────────────────────────────────────────────

export interface StockQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  marketCap: number;
  peRatio: number | null;
  pbRatio: number | null;
  divYield: number | null;
  open: number;
  dayHigh: number;
  dayLow: number;
  high52w: number;
  low52w: number;
  prevClose: number;
}

export interface OHLCV {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// ─── Quote ────────────────────────────────────────────────

export async function getQuote(symbol: string): Promise<StockQuote> {
  try {
    const ySymbol = toYahooSymbol(symbol);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const q: any = await yahooFinance.quote(ySymbol);

    return {
      symbol,
      name: q.shortName ?? q.longName ?? symbol,
      price: q.regularMarketPrice ?? 0,
      change: q.regularMarketChange ?? 0,
      changePct: q.regularMarketChangePercent ?? 0,
      volume: q.regularMarketVolume ?? 0,
      marketCap: q.marketCap ?? 0,
      peRatio: q.trailingPE ?? null,
      pbRatio: q.priceToBook ?? null,
      divYield: q.dividendYield ?? null,
      open: q.regularMarketOpen ?? 0,
      dayHigh: q.regularMarketDayHigh ?? 0,
      dayLow: q.regularMarketDayLow ?? 0,
      high52w: q.fiftyTwoWeekHigh ?? 0,
      low52w: q.fiftyTwoWeekLow ?? 0,
      prevClose: q.regularMarketPreviousClose ?? 0,
    };
  } catch {
    // Fall back to mock data
    const detail = getInstrumentDetail(symbol);
    return {
      symbol: detail.symbol,
      name: detail.name,
      price: detail.currentPrice,
      change: detail.change,
      changePct: detail.changePct,
      volume: detail.volume,
      marketCap: detail.marketCap,
      peRatio: detail.peRatio,
      pbRatio: detail.pbRatio,
      divYield: detail.divYield,
      open: detail.open,
      dayHigh: detail.dayHigh,
      dayLow: detail.dayLow,
      high52w: detail.high52w,
      low52w: detail.low52w,
      prevClose: detail.prevClose,
    };
  }
}

// ─── Historical OHLCV ────────────────────────────────────

type Period = '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y' | 'max';

export async function getHistoricalOHLCV(
  symbol: string,
  period: Period = '6mo',
): Promise<OHLCV[]> {
  try {
    const ySymbol = toYahooSymbol(symbol);
    const now = new Date();
    const periodMap: Record<Period, number> = {
      '1mo': 30,
      '3mo': 90,
      '6mo': 180,
      '1y': 365,
      '2y': 730,
      '5y': 1825,
      max: 3650,
    };
    const days = periodMap[period] ?? 180;
    const period1 = new Date(now.getTime() - days * 86_400_000);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const rows: any[] = await yahooFinance.historical(ySymbol, {
      period1,
      period2: now,
    });

    return rows.map((r: { date: Date; open: number; high: number; low: number; close: number; volume: number }) => ({
      date: r.date.toISOString().split('T')[0]!,
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
      volume: r.volume,
    }));
  } catch {
    // Fall back to mock OHLCV
    const detail = getInstrumentDetail(symbol);
    return generateOHLCV(detail.currentPrice, period === '1mo' ? 30 : 120);
  }
}

// ─── Batch Quotes ─────────────────────────────────────────

const BATCH_SIZE = 10;
const BATCH_DELAY_MS = 100;

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

export async function getBatchQuotes(symbols: string[]): Promise<StockQuote[]> {
  const results: StockQuote[] = [];

  for (let i = 0; i < symbols.length; i += BATCH_SIZE) {
    const batch = symbols.slice(i, i + BATCH_SIZE);
    const quotes = await Promise.all(batch.map((s) => getQuote(s)));
    results.push(...quotes);
    if (i + BATCH_SIZE < symbols.length) {
      await delay(BATCH_DELAY_MS);
    }
  }

  return results;
}

// ─── IDX Stock List ───────────────────────────────────────

export const IDX_STOCK_LIST = [
  'BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII',
  'UNVR', 'GOTO', 'BREN', 'PANI', 'EMTK',
  'ICBP', 'INDF', 'KLBF', 'PGAS', 'SMGR',
  'ADRO', 'ANTM', 'BBNI', 'CPIN', 'EXCL',
  'GGRM', 'HMSP', 'INCO', 'ISAT', 'JPFA',
  'JSMR', 'MDKA', 'MEDC', 'MIKA', 'PTBA',
  'TBIG', 'TOWR', 'ACES', 'BBTN', 'BRIS',
  'BRPT', 'ESSA', 'HRUM',
] as const;

// ─── Index Data ───────────────────────────────────────────

export interface IndexQuote {
  symbol: string;
  name: string;
  value: number;
  change: number;
  changePct: number;
}

export async function getIndexData(): Promise<IndexQuote[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const q: any = await yahooFinance.quote('^JKSE');
    return [
      {
        symbol: 'IHSG',
        name: 'Jakarta Composite',
        value: q.regularMarketPrice ?? 0,
        change: q.regularMarketChange ?? 0,
        changePct: q.regularMarketChangePercent ?? 0,
      },
      // Additional indices fall back to mock since Yahoo doesn't carry all IDX indices
      ...INDICES.filter((idx) => idx.symbol !== 'IHSG').map((idx) => ({
        symbol: idx.symbol,
        name: idx.name,
        value: idx.value,
        change: idx.change,
        changePct: idx.changePct,
      })),
    ];
  } catch {
    return INDICES.map((idx) => ({
      symbol: idx.symbol,
      name: idx.name,
      value: idx.value,
      change: idx.change,
      changePct: idx.changePct,
    }));
  }
}

// Re-export mock helpers for fallback usage in routes
export { POSITIONS, INDICES, generateScreenerData };
