'use client';

import { useState } from 'react';
import Link from 'next/link';

export function RegisterForm() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    confirm_password: '',
  });
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    // In production, call /v1/auth/register
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="text-center">
        <h3 className="text-lg font-medium text-text-primary">Account created</h3>
        <p className="mt-2 text-sm text-text-secondary">Check your email to verify your account.</p>
        <Link href="/login" className="mt-4 inline-block text-sm text-accent-500 hover:text-accent-600">
          Go to login
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md bg-negative/10 px-3 py-2 text-sm text-negative">{error}</div>
      )}
      <div>
        <label htmlFor="full_name" className="block text-sm font-medium text-text-secondary mb-1">Full Name</label>
        <input id="full_name" type="text" required value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none" />
      </div>
      <div>
        <label htmlFor="reg-email" className="block text-sm font-medium text-text-secondary mb-1">Email</label>
        <input id="reg-email" type="email" required value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none" />
      </div>
      <div>
        <label htmlFor="reg-password" className="block text-sm font-medium text-text-secondary mb-1">Password</label>
        <input id="reg-password" type="password" required value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none" placeholder="Min. 8 characters" />
      </div>
      <div>
        <label htmlFor="confirm-password" className="block text-sm font-medium text-text-secondary mb-1">Confirm Password</label>
        <input id="confirm-password" type="password" required value={formData.confirm_password} onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })} className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none" />
      </div>
      <button type="submit" className="w-full rounded-md bg-accent-500 px-4 py-2.5 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors">
        Create Account
      </button>
      <p className="text-center text-sm text-text-muted">
        Already have an account?{' '}
        <Link href="/login" className="text-accent-500 hover:text-accent-600">Log in</Link>
      </p>
    </form>
  );
}
