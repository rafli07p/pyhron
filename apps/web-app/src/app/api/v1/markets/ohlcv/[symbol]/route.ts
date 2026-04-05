import { NextResponse } from 'next/server';
import { getHistoricalOHLCV } from '@/lib/market-data';

const VALID_PERIODS = ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'] as const;
type Period = (typeof VALID_PERIODS)[number];

function isValidPeriod(p: string): p is Period {
  return (VALID_PERIODS as readonly string[]).includes(p);
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const { searchParams } = new URL(request.url);
  const periodParam = searchParams.get('period') ?? '6mo';
  const period: Period = isValidPeriod(periodParam) ? periodParam : '6mo';

  const data = await getHistoricalOHLCV(symbol.toUpperCase(), period);

  return NextResponse.json(data, {
    headers: {
      'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
    },
  });
}
