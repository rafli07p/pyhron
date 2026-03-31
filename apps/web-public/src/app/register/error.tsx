'use client';

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

const errorMessages: Record<string, string> = {
  CredentialsSignin: 'Invalid email or password',
  SessionRequired: 'Please sign in to continue',
  Default: 'Authentication error',
};

export default function AuthError() {
  const searchParams = useSearchParams();
  const errorType = searchParams.get('error') || 'Default';
  const message = errorMessages[errorType] || errorMessages.Default;

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 text-center">
      <h1 className="font-display text-2xl text-text-primary">Authentication Error</h1>
      <p className="mt-4 text-text-secondary">{message}</p>
      <Link
        href="/login"
        className="mt-6 rounded-md bg-accent-500 px-6 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
      >
        Back to login
      </Link>
    </div>
  );
}
