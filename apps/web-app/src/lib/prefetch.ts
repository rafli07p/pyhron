import type { QueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/query-keys';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export function prefetchInstrument(qc: QueryClient, symbol: string) {
  qc.prefetchQuery({
    queryKey: queryKeys.markets.instrument(symbol),
    queryFn: () => fetchJson(`${API}/v1/market/instruments/${symbol}`),
    staleTime: 30_000,
  });
}

export function prefetchBacktest(qc: QueryClient, id: string) {
  qc.prefetchQuery({
    queryKey: queryKeys.strategies.backtest(id),
    queryFn: () => fetchJson(`${API}/v1/backtest/${id}`),
    staleTime: 60_000,
  });
}

export function prefetchStrategy(qc: QueryClient, id: string) {
  qc.prefetchQuery({
    queryKey: queryKeys.strategies.detail(id),
    queryFn: () => fetchJson(`${API}/v1/strategies/${id}`),
    staleTime: 30_000,
  });
}
