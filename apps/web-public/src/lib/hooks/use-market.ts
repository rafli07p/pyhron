import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { MarketOverview, InstrumentResponse, OHLCVBar } from '@/types/market';

export function useMarketOverview() {
  return useQuery<MarketOverview>({
    queryKey: ['market', 'overview'],
    queryFn: () => api.get('/market/overview'),
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 2,
  });
}

export function useInstruments(params?: { sector?: string; lq45Only?: boolean }) {
  return useQuery<InstrumentResponse[]>({
    queryKey: ['market', 'instruments', params],
    queryFn: () => {
      const sp = new URLSearchParams();
      if (params?.sector) sp.set('sector', params.sector);
      if (params?.lq45Only) sp.set('lq45_only', 'true');
      return api.get(`/market/instruments?${sp}`);
    },
    staleTime: 5 * 60_000,
  });
}

export function useOHLCV(symbol: string, interval = 'daily', limit = 365) {
  return useQuery<OHLCVBar[]>({
    queryKey: ['market', 'ohlcv', symbol, interval, limit],
    queryFn: () => api.get(`/market/ohlcv/${symbol}?interval=${interval}&limit=${limit}`),
    enabled: !!symbol,
    staleTime: 60_000,
  });
}
