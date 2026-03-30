import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { BacktestResultResponse, BacktestMetrics } from '@/types/backtest';

export function useBacktestResult(taskId: string) {
  return useQuery<BacktestResultResponse>({
    queryKey: ['backtest', taskId],
    queryFn: () => api.get(`/backtest/${taskId}`),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'running' ? 5000 : false;
    },
  });
}

export function useBacktestMetrics(taskId: string) {
  return useQuery<BacktestMetrics>({
    queryKey: ['backtest', taskId, 'metrics'],
    queryFn: () => api.get(`/backtest/${taskId}/metrics`),
    enabled: !!taskId,
  });
}
