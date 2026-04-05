import { NextResponse } from 'next/server';
import { getIndexData } from '@/lib/market-data';

export async function GET() {
  const indices = await getIndexData();

  return NextResponse.json(indices, {
    headers: {
      'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=60',
    },
  });
}
