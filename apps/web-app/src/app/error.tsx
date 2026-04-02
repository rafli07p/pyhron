'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/design-system/primitives/Button';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to Sentry when configured
  }, [error]);

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[var(--surface-0)]">
      <AlertTriangle className="h-10 w-10 text-[var(--warning)]" />
      <h2 className="text-lg font-semibold text-[var(--text-primary)]">Something went wrong</h2>
      <p className="max-w-md text-center text-sm text-[var(--text-secondary)]">
        {error.message || 'An unexpected error occurred. Please try again.'}
      </p>
      <Button onClick={reset} variant="outline">
        <RefreshCw className="mr-2 h-4 w-4" />
        Try again
      </Button>
    </div>
  );
}
