import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { NewsArticle, SentimentSummaryResponse } from '@/types/news';

export function useNews(params?: { symbol?: string; limit?: number }) {
  return useQuery<NewsArticle[]>({
    queryKey: ['news', params],
    queryFn: () => {
      const sp = new URLSearchParams();
      if (params?.symbol) sp.set('symbol', params.symbol);
      if (params?.limit) sp.set('limit', String(params.limit));
      return api.get(`/news/articles?${sp}`);
    },
    staleTime: 2 * 60_000,
  });
}

export function useSentiment(symbols: string[]) {
  return useQuery<SentimentSummaryResponse>({
    queryKey: ['news', 'sentiment', symbols],
    queryFn: () => api.get(`/news/sentiment?symbols=${symbols.join(',')}`),
    enabled: symbols.length > 0,
    staleTime: 5 * 60_000,
  });
}
