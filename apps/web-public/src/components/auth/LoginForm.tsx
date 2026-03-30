'use client';

import { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await signIn('credentials', {
      email,
      password,
      redirect: false,
    });

    if (result?.error) {
      setError(result.error === 'CredentialsSignin' ? 'Invalid email or password' : result.error);
      setLoading(false);
    } else {
      router.push('/dashboard/overview');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md bg-negative/10 px-3 py-2 text-sm text-negative">{error}</div>
      )}
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-1">Email</label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none"
          placeholder="you@company.com"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1">Password</label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none"
          placeholder="Min. 8 characters"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-accent-500 px-4 py-2.5 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors disabled:opacity-50"
      >
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
      <p className="text-center text-sm text-text-muted">
        No account?{' '}
        <Link href="/register" className="text-accent-500 hover:text-accent-600">
          Register
        </Link>
      </p>
    </form>
  );
}
