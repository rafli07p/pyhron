import type { Metadata } from 'next';
import { LoginForm } from '@/components/auth/LoginForm';

export const metadata: Metadata = { title: 'Log In' };

export default function LoginPage() {
  return (
    <div className="w-full max-w-md">
      <h1 className="font-display text-2xl text-text-primary text-center">Log in to Pyhron</h1>
      <p className="mt-2 text-center text-sm text-text-secondary">
        Access your dashboard, strategies, and research.
      </p>
      <div className="mt-8">
        <LoginForm />
      </div>
    </div>
  );
}
