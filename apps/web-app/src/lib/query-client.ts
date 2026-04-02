import { QueryClient, MutationCache, QueryCache } from '@tanstack/react-query';
import { AuthError, RateLimitError, NetworkError } from './api-client';

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60 * 1000,
        retry: (failureCount, error) => {
          if (error instanceof AuthError) return false;
          if (error instanceof RateLimitError) return false;
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * Math.pow(2, attemptIndex), 30_000),
        refetchOnWindowFocus: 'always',
        refetchOnReconnect: 'always',
      },
      mutations: {
        retry: false,
      },
    },
    queryCache: new QueryCache({
      onError: (error) => {
        if (!(error instanceof AuthError) && !(error instanceof NetworkError)) {
          // Report to Sentry when configured
        }
      },
    }),
    mutationCache: new MutationCache({
      onError: (error) => {
        if (error instanceof NetworkError) {
          // Toast: network error
        } else if (error instanceof RateLimitError) {
          // Toast: rate limited
        }
      },
    }),
  });
}
