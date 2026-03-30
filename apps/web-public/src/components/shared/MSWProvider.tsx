'use client';

import { useEffect, useRef } from 'react';

export function MSWProvider({ children }: { children: React.ReactNode }) {
  const started = useRef(false);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_USE_MSW === 'true' && !started.current) {
      started.current = true;
      import('@/lib/mock/browser')
        .then(({ worker }) => worker.start({ onUnhandledRequest: 'bypass' }))
        .catch(() => {});
    }
  }, []);

  return <>{children}</>;
}
