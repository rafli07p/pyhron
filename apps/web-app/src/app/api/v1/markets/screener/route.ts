import { NextResponse } from 'next/server';
import { getBatchQuotes, IDX_STOCK_LIST } from '@/lib/market-data';

export async function GET() {
  const quotes = await getBatchQuotes([...IDX_STOCK_LIST]);

  return NextResponse.json(quotes, {
    headers: {
      'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120',
    },
  });
}
