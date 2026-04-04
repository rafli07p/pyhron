'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

/**
 * Cleans up stale React Query cache entries every 30 minutes.
 * Prevents memory accumulation during 8+ hour trading sessions.
 * Call once in AppProviders.
 */
export function useMemoryGuard() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const interval = setInterval(
      () => {
        const cache = queryClient.getQueryCache();
        const now = Date.now();

        cache.getAll().forEach((query) => {
          const age = now - query.state.dataUpdatedAt;
          const observers = query.getObserversCount();
          // Remove queries not observed and older than 10 minutes
          if (observers === 0 && age > 10 * 60 * 1000) {
            queryClient.removeQueries({ queryKey: query.queryKey, exact: true });
          }
        });
      },
      30 * 60 * 1000,
    );

    return () => clearInterval(interval);
  }, [queryClient]);
}
