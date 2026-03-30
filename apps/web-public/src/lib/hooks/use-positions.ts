import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { PositionResponse, OrderResponse, PaperSessionResponse, RiskSnapshotResponse } from '@/types/trading';

export function usePositions(strategyId: string) {
  return useQuery<PositionResponse[]>({
    queryKey: ['positions', strategyId],
    queryFn: () => api.get(`/paper/${strategyId}/positions`),
    enabled: !!strategyId,
    staleTime: 30_000,
  });
}

export function useOrders(strategyId: string) {
  return useQuery<OrderResponse[]>({
    queryKey: ['orders', strategyId],
    queryFn: () => api.get(`/paper/${strategyId}/orders`),
    enabled: !!strategyId,
    staleTime: 30_000,
  });
}

export function usePaperSessions() {
  return useQuery<PaperSessionResponse[]>({
    queryKey: ['paper', 'sessions'],
    queryFn: () => api.get('/paper/sessions'),
    staleTime: 30_000,
  });
}

export function useRiskSnapshot(strategyId: string) {
  return useQuery<RiskSnapshotResponse>({
    queryKey: ['risk', strategyId],
    queryFn: () => api.get(`/risk/${strategyId}/snapshot`),
    enabled: !!strategyId,
    staleTime: 30_000,
  });
}
