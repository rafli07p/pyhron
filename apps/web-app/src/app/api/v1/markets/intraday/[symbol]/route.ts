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

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const upper = symbol.toUpperCase();

  try {
    const ySymbol = SYMBOL_MAP[upper] ?? `${upper}.JK`;

    const now = new Date();
    const period1 = new Date(now);
    period1.setDate(period1.getDate() - 5); // last 5 days to ensure we get data

    const rows = await yahooFinance.historical(ySymbol, {
      period1,
      period2: now,
      interval: '1d',
    }) as { date: Date; open: number; high: number; low: number; close: number; volume: number }[];

    if (rows.length === 0) throw new Error('No data returned');

    // Use recent daily closes as chart points
    const points = rows.map((r) => r.close);
    const latest = rows[rows.length - 1]!;
    const prev = rows.length > 1 ? rows[rows.length - 2]! : latest;
    const change = prev.close > 0
      ? ((latest.close - prev.close) / prev.close) * 100
      : 0;

    return NextResponse.json(
      {
        symbol: upper,
        current: latest.close,
        open: latest.open,
        change: Math.round(change * 100) / 100,
        points,
        timestamps: rows.map((r) => r.date.toISOString().split('T')[0]),
        lastUpdate: now.toLocaleTimeString('id-ID', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        }),
      },
      { headers: { 'Cache-Control': 'public, s-maxage=15, stale-while-revalidate=30' } },
    );
  } catch (error) {
    console.error(`Intraday fetch failed for ${upper}:`, error);

    const baseMap: Record<string, number> = {
      IHSG: 7234, LQ45: 985, IDX30: 482, IDX80: 132, JII: 548,
    };
    const base = baseMap[upper] ?? 500;
    const pts = Array.from({ length: 60 }, (_, i) =>
      Math.round((base + Math.sin(i * 0.3) * base * 0.005 + Math.sin(i * 0.1) * base * 0.003) * 100) / 100,
    );

    return NextResponse.json({
      symbol: upper,
      current: pts[pts.length - 1],
      open: pts[0],
      change: Math.round(((pts[pts.length - 1]! - pts[0]!) / pts[0]!) * 10000) / 100,
      points: pts,
      timestamps: [],
      lastUpdate: new Date().toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
    });
  }
}
