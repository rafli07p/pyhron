'use client';

import Link from 'next/link';

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-content flex-col items-center justify-center px-6 text-center">
      <h1 className="font-display text-3xl text-text-primary">Unexpected error</h1>
      <p className="mt-4 text-text-secondary">
        Something went wrong. Please try again or return to the homepage.
      </p>
      <div className="mt-8 flex gap-4">
        <button
          onClick={reset}
          className="rounded-md bg-accent-500 px-6 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-md border border-border px-6 py-2 text-sm font-medium hover:bg-bg-tertiary transition-colors"
        >
          Go home
        </Link>
      </div>
    </div>
  );
}
