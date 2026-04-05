import { NextResponse } from 'next/server';
import { getQuote } from '@/lib/market-data';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const quote = await getQuote(symbol.toUpperCase());

  return NextResponse.json(quote, {
    headers: {
      'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=60',
    },
  });
}
