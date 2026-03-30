'use client';

import { useEffect, useState } from 'react';

export function MSWProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(process.env.NEXT_PUBLIC_USE_MSW !== 'true');

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_USE_MSW === 'true') {
      import('@/lib/mock/browser').then(({ worker }) => {
        worker.start({ onUnhandledRequest: 'bypass' }).then(() => setReady(true));
      });
    }
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}
