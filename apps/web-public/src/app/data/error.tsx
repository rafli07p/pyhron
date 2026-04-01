'use client';

import { useState } from 'react';

export default function PlatformError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-content flex-col items-center justify-center px-6 text-center">
      <h1 className="font-display text-2xl text-text-primary">
        Something went wrong loading this data
      </h1>
      <p className="mt-4 text-text-secondary">
        The data could not be loaded. Please try again.
      </p>
      <button
        onClick={reset}
        className="mt-6 rounded-md bg-accent-500 px-6 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
      >
        Retry
      </button>
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="mt-4 text-xs text-text-muted hover:text-text-secondary"
      >
        {showDetails ? 'Hide' : 'Show'} details
      </button>
      {showDetails && (
        <pre className="mt-2 max-w-md overflow-auto rounded border border-border bg-bg-tertiary p-3 text-left text-xs text-text-secondary">
          {error.message}
        </pre>
      )}
    </div>
  );
}
