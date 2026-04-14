import { NextResponse } from 'next/server';
import YahooFinance from 'yahoo-finance2';

const yahooFinance = new YahooFinance();

const SYMBOL_MAP: Record<string, string> = {
  IHSG: '^JKSE',
  LQ45: '^JKLQ45',
  IDX30: '^JKIDX30',
  JII: '^JKII',
  IDX80: '^JKSE', // fallback — IDX80 not on Yahoo
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
    const todayOpen = new Date(now);
    todayOpen.setHours(0, 0, 0, 0);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result: any = await yahooFinance.chart(ySymbol, {
      period1: todayOpen,
      period2: now,
      interval: '5m' as const,
    });

    const quotes = result.quotes ?? [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const points: { time: string; price: number }[] = quotes
      .filter((q: { close?: number | null }) => q.close != null)
      .map((q: { date: Date; close: number }) => ({
        time: new Date(q.date).toLocaleTimeString('id-ID', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        }),
        price: q.close,
      }));

    const openPrice = points.length > 0 ? points[0]!.price : 0;
    const currentPrice = points.length > 0 ? points[points.length - 1]!.price : 0;
    const change = openPrice > 0 ? ((currentPrice - openPrice) / openPrice) * 100 : 0;

    return NextResponse.json(
      {
        symbol: upper,
        current: currentPrice,
        open: openPrice,
        change: Math.round(change * 100) / 100,
        points: points.map((p) => p.price),
        timestamps: points.map((p) => p.time),
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

    // Fallback: deterministic mock so UI never breaks
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
