import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { MacroIndicator, IndicatorHistory, YieldCurvePoint, PolicyEvent } from '@/types/macro';

export function useMacroIndicators() {
  return useQuery<MacroIndicator[]>({
    queryKey: ['macro', 'indicators'],
    queryFn: () => api.get('/macro/indicators'),
    staleTime: 5 * 60_000,
  });
}

export function useIndicatorHistory(code: string) {
  return useQuery<IndicatorHistory>({
    queryKey: ['macro', 'history', code],
    queryFn: () => api.get(`/macro/indicators/${code}/history`),
    enabled: !!code,
    staleTime: 5 * 60_000,
  });
}

export function useYieldCurve() {
  return useQuery<YieldCurvePoint[]>({
    queryKey: ['macro', 'yield-curve'],
    queryFn: () => api.get('/macro/yield-curve'),
    staleTime: 5 * 60_000,
  });
}

export function usePolicyCalendar() {
  return useQuery<PolicyEvent[]>({
    queryKey: ['macro', 'policy-calendar'],
    queryFn: () => api.get('/macro/policy-calendar'),
    staleTime: 5 * 60_000,
  });
}
