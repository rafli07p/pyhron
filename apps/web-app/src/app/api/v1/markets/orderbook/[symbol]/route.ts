import { NextResponse } from 'next/server';
import { generateOrderbook } from '@/mocks/generators/orderbook';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const snapshot = generateOrderbook(symbol.toUpperCase());
  return NextResponse.json(snapshot, {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
