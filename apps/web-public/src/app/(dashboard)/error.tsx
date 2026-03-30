'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    if (error.message === 'RefreshTokenError') {
      router.push('/login');
    }
  }, [error, router]);

  if (error.message === 'RefreshTokenError') return null;

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-content flex-col items-center justify-center px-6 text-center">
      <h1 className="font-display text-2xl text-text-primary">Dashboard error</h1>
      <p className="mt-4 text-text-secondary">
        Something went wrong loading the dashboard.
      </p>
      <button
        onClick={reset}
        className="mt-6 rounded-md bg-accent-500 px-6 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}
