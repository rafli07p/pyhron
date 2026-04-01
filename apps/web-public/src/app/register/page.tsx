import type { Metadata } from 'next';
import { RegisterForm } from '@/components/auth/RegisterForm';

export const metadata: Metadata = { title: 'Register' };

export default function RegisterPage() {
  return (
    <div className="w-full max-w-md">
      <h1 className="font-display text-2xl text-text-primary text-center">Create an Account</h1>
      <p className="mt-2 text-center text-sm text-text-secondary">
        Start with free access to the IDX screener and 100 API calls per day.
      </p>
      <div className="mt-8">
        <RegisterForm />
      </div>
    </div>
  );
}
