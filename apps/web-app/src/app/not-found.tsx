import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--surface-0)] px-6">
      <p className="font-mono text-[120px] font-bold leading-none text-[var(--text-primary)]/5">
        404
      </p>
      <h1 className="mt-4 text-xl font-semibold text-[var(--text-primary)]">Page not found</h1>
      <p className="mt-2 max-w-md text-center text-sm text-[var(--text-secondary)]">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <div className="mt-8 flex items-center gap-4">
        <Link
          href="/"
          className="rounded-lg bg-[var(--accent-500)] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
        >
          Back to Home
        </Link>
        <Link
          href="/contact"
          className="text-sm text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-secondary)]"
        >
          Contact Support
        </Link>
      </div>
    </div>
  );
}
