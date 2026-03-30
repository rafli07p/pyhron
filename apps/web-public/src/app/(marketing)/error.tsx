'use client';

import Link from 'next/link';

export default function MarketingError() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-content flex-col items-center justify-center px-6 text-center">
      <h1 className="font-display text-2xl text-text-primary">Something went wrong</h1>
      <p className="mt-4 text-text-secondary">
        We could not load this page. Please try again later.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-md bg-accent-500 px-6 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
      >
        Back to home
      </Link>
    </div>
  );
}
