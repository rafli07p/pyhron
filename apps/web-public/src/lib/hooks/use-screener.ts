import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { ScreenerResponse, ScreenerParams } from '@/types/screener';

export function useScreener(params: ScreenerParams) {
  return useQuery<ScreenerResponse>({
    queryKey: ['screener', params],
    queryFn: () => {
      const sp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) sp.set(k, String(v));
      });
      return api.get(`/screener/screen?${sp}`);
    },
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}
