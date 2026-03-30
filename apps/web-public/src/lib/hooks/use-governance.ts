import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { GovernanceFlag, OwnershipChange, AuditOpinion } from '@/types/governance';

export function useGovernanceFlags(symbol?: string) {
  return useQuery<GovernanceFlag[]>({
    queryKey: ['governance', 'flags', symbol],
    queryFn: () => api.get(`/governance/flags${symbol ? `?symbol=${symbol}` : ''}`),
    staleTime: 5 * 60_000,
  });
}

export function useOwnershipChanges(symbol: string) {
  return useQuery<OwnershipChange[]>({
    queryKey: ['governance', 'ownership', symbol],
    queryFn: () => api.get(`/governance/ownership/${symbol}`),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  });
}

export function useAuditOpinions(symbol: string) {
  return useQuery<AuditOpinion[]>({
    queryKey: ['governance', 'audit', symbol],
    queryFn: () => api.get(`/governance/audit/${symbol}`),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  });
}
