import { useQuery } from '@tanstack/react-query';
import type { StockQuote, OHLCV, IndexQuote } from '@/lib/market-data';

// ─── Fetchers ─────────────────────────────────────────────

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<T>;
}

// ─── Hooks ────────────────────────────────────────────────

export function useQuote(symbol: string) {
  return useQuery<StockQuote>({
    queryKey: ['quote', symbol],
    queryFn: () => fetchJson(`/api/v1/markets/quote/${encodeURIComponent(symbol)}`),
    staleTime: 30_000,
    refetchInterval: 30_000,
    enabled: !!symbol,
  });
}

export function useOHLCV(symbol: string, period = '6mo') {
  return useQuery<OHLCV[]>({
    queryKey: ['ohlcv', symbol, period],
    queryFn: () =>
      fetchJson(`/api/v1/markets/ohlcv/${encodeURIComponent(symbol)}?period=${period}`),
    staleTime: 5 * 60_000,
    enabled: !!symbol,
  });
}

export function useScreener(options?: { enabled?: boolean }) {
  return useQuery<StockQuote[]>({
    queryKey: ['screener', options],
    queryFn: () => fetchJson('/api/v1/markets/screener'),
    staleTime: 60_000,
    enabled: options?.enabled ?? true,
  });
}

export function useIndices() {
  return useQuery<IndexQuote[]>({
    queryKey: ['indices'],
    queryFn: () => fetchJson('/api/v1/markets/indices'),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
