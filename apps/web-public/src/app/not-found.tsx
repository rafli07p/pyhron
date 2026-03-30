import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-content flex-col items-center justify-center px-6 text-center">
      <h1 className="font-display text-8xl text-text-muted">404</h1>
      <p className="mt-4 text-xl text-text-secondary">Page not found</p>
      <p className="mt-2 text-text-muted">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-md bg-accent-500 px-6 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
      >
        Back to homepage
      </Link>
    </div>
  );
}
