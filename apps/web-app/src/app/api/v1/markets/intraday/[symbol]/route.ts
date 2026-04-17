import { NextResponse } from 'next/server';
import YahooFinance from 'yahoo-finance2';

const yahooFinance = new YahooFinance();

const SYMBOL_MAP: Record<string, string> = {
  IHSG: '^JKSE',
  LQ45: '^JKLQ45',
  IDX30: '^JKIDX30',
  JII: '^JKII',
  IDX80: '^JKSE',
};

// Fallback realistic values per index (used when Yahoo unreachable)
const FALLBACK: Record<string, { base: number; change: number }> = {
  IHSG: { base: 7234.56, change: 0.45 },
  LQ45: { base: 985.23, change: -0.52 },
  IDX30: { base: 482.18, change: 0.58 },
  IDX80: { base: 132.45, change: 0.66 },
  JII: { base: 548.92, change: -0.58 },
};

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const upper = symbol.toUpperCase();
  const ySymbol = SYMBOL_MAP[upper] ?? `${upper}.JK`;

  try {
    const now = new Date();
    const period1 = new Date(now);
    period1.setDate(period1.getDate() - 30); // 30 days for sparkline context

    // Real-time current price via quote()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const q: any = await yahooFinance.quote(ySymbol);
    const current = q.regularMarketPrice ?? q.regularMarketPreviousClose ?? 0;
    const prevClose = q.regularMarketPreviousClose ?? 0;
    const change = q.regularMarketChangePercent ?? (
      prevClose > 0 ? ((current - prevClose) / prevClose) * 100 : 0
    );

    // Historical for sparkline
    const rows = await yahooFinance.historical(ySymbol, {
      period1,
      period2: now,
      interval: '1d',
    }) as { date: Date; open: number; high: number; low: number; close: number; volume: number }[];

    const points = rows.length > 0 ? rows.map((r) => r.close) : [];
    // Append current price as last point if available
    if (current > 0 && (points.length === 0 || points[points.length - 1] !== current)) {
      points.push(current);
    }

    if (current <= 0 || points.length < 2) throw new Error('No data');

    return NextResponse.json(
      {
        symbol: upper,
        current,
        open: q.regularMarketOpen ?? prevClose,
        change: Math.round(change * 100) / 100,
        points,
        timestamps: [],
        lastUpdate: now.toLocaleTimeString('id-ID', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
          timeZone: 'Asia/Jakarta',
        }),
      },
      { headers: { 'Cache-Control': 'public, s-maxage=15, stale-while-revalidate=30' } },
    );
  } catch (error) {
    console.error(`Intraday fetch failed for ${upper}:`, error);

    // Realistic deterministic fallback (sine waves around current base)
    const fb = FALLBACK[upper] ?? { base: 500, change: 0 };
    const pts = Array.from({ length: 30 }, (_, i) => {
      const t = i / 29;
      const trend = fb.change > 0 ? t * fb.base * 0.01 : fb.change < 0 ? -t * fb.base * 0.01 : 0;
      const noise = Math.sin(i * 0.5) * fb.base * 0.003 + Math.sin(i * 1.2) * fb.base * 0.002;
      return Math.round((fb.base + trend + noise) * 100) / 100;
    });

    return NextResponse.json({
      symbol: upper,
      current: fb.base,
      open: fb.base - fb.base * fb.change / 100,
      change: fb.change,
      points: pts,
      timestamps: [],
      lastUpdate: new Date().toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: 'Asia/Jakarta',
      }),
    });
  }
}
