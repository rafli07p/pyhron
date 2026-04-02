'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Logo } from '@/components/common/Logo';
import { Button } from '@/design-system/primitives/Button';
import { Input } from '@/design-system/primitives/Input';
import { Alert, AlertDescription } from '@/design-system/primitives/Alert';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const reason = searchParams.get('reason');

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    const result = await signIn('credentials', {
      email: data.email,
      password: data.password,
      redirect: false,
    });

    if (result?.error) {
      setError(result.error);
    } else {
      router.push('/dashboard');
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Logo size="lg" />
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          Sign in to your account
        </p>
      </div>

      {reason === 'session_expired' && (
        <Alert variant="warning">
          <AlertDescription>Your session has expired. Please sign in again.</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="negative">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          error={errors.email?.message}
          autoComplete="email"
          {...register('email')}
        />
        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          error={errors.password?.message}
          autoComplete="current-password"
          {...register('password')}
        />

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Sign In
        </Button>
      </form>

      <div className="space-y-2 text-center text-sm">
        <Link
          href="/forgot-password"
          className="text-[var(--accent-500)] hover:text-[var(--accent-600)]"
        >
          Forgot password?
        </Link>
        <p className="text-[var(--text-tertiary)]">
          Don&apos;t have an account?{' '}
          <Link
            href="/register"
            className="text-[var(--accent-500)] hover:text-[var(--accent-600)]"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
