'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--surface-0)] px-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--danger)]/10">
        <svg className="h-6 w-6 text-[var(--danger)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
      </div>

      <h1 className="mt-6 text-xl font-semibold text-[var(--text-primary)]">Something went wrong</h1>
      <p className="mt-2 max-w-md text-center text-sm text-[var(--text-secondary)]">
        An unexpected error occurred. Our team has been notified.
      </p>

      <div className="mt-8 flex items-center gap-4">
        <button
          onClick={reset}
          className="rounded-lg bg-[var(--accent-500)] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
        >
          Try Again
        </button>
        <Link
          href="/"
          className="rounded-lg border border-[var(--border-primary)] px-5 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-2)]"
        >
          Back to Home
        </Link>
      </div>

      <button
        onClick={() => setShowDetails((v) => !v)}
        className="mt-6 text-xs text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-secondary)]"
      >
        {showDetails ? 'Hide details' : 'Show details'}
      </button>

      {showDetails && (
        <pre className="mt-3 max-w-lg overflow-auto rounded-lg bg-[var(--surface-2)] p-4 text-xs text-[var(--text-tertiary)]">
          {error.message || 'No error message available.'}
          {error.digest && `\n\nDigest: ${error.digest}`}
        </pre>
      )}
    </div>
  );
}
