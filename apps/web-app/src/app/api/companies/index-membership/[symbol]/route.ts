import { NextResponse } from 'next/server';

import { AVAILABLE_PEERS, BBCA_INDEX_ROWS } from '@/lib/index-composition/data';
import type { IndexMembershipResponse } from '@/lib/index-composition/types';

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const body: IndexMembershipResponse = {
    symbol: symbol.toUpperCase(),
    industry: 'Banks',
    asOfDate: '2025-09-30',
    availablePeers: AVAILABLE_PEERS,
    rows: BBCA_INDEX_ROWS,
  };
  return NextResponse.json(body, {
    headers: { 'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300' },
  });
}
