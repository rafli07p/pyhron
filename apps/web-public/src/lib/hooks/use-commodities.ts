import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { CommodityDashboard, CommodityHistory } from '@/types/commodity';

export function useCommodityDashboard() {
  return useQuery<CommodityDashboard>({
    queryKey: ['commodities', 'dashboard'],
    queryFn: () => api.get('/commodities/dashboard'),
    staleTime: 5 * 60_000,
  });
}

export function useCommodityHistory(code: string) {
  return useQuery<CommodityHistory>({
    queryKey: ['commodities', 'history', code],
    queryFn: () => api.get(`/commodities/${code}/history`),
    enabled: !!code,
    staleTime: 5 * 60_000,
  });
}
