import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { StrategyResponse, StrategyPerformance } from '@/types/strategy';

export function useStrategies() {
  return useQuery<StrategyResponse[]>({
    queryKey: ['strategies'],
    queryFn: () => api.get('/strategies/'),
    staleTime: 30_000,
  });
}

export function useStrategyPerformance(strategyId: string) {
  return useQuery<StrategyPerformance>({
    queryKey: ['strategies', strategyId, 'performance'],
    queryFn: () => api.get(`/strategies/${strategyId}/performance`),
    enabled: !!strategyId,
  });
}

export function useToggleStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enable }: { id: string; enable: boolean }) =>
      api.post(`/strategies/${id}/${enable ? 'enable' : 'disable'}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategies'] }),
  });
}
