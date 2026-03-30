import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { GovernmentBond, CorporateBond, CreditSpread } from '@/types/fixed-income';

export function useGovernmentBonds() {
  return useQuery<GovernmentBond[]>({
    queryKey: ['bonds', 'government'],
    queryFn: () => api.get('/bonds/government'),
    staleTime: 5 * 60_000,
  });
}

export function useCorporateBonds() {
  return useQuery<CorporateBond[]>({
    queryKey: ['bonds', 'corporate'],
    queryFn: () => api.get('/bonds/corporate'),
    staleTime: 5 * 60_000,
  });
}

export function useCreditSpreads() {
  return useQuery<CreditSpread[]>({
    queryKey: ['bonds', 'credit-spreads'],
    queryFn: () => api.get('/bonds/credit-spreads'),
    staleTime: 5 * 60_000,
  });
}
