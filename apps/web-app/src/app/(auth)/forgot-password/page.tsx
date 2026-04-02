'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Logo } from '@/components/common/Logo';
import { Button } from '@/design-system/primitives/Button';
import { Input } from '@/design-system/primitives/Input';
import { Alert, AlertDescription } from '@/design-system/primitives/Alert';

const schema = z.object({
  email: z.string().email('Invalid email address'),
});

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(schema),
  });

  const onSubmit = async () => {
    setSent(true);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Logo size="lg" />
        <p className="mt-2 text-sm text-[var(--text-secondary)]">Reset your password</p>
      </div>

      {sent ? (
        <Alert variant="positive">
          <AlertDescription>
            If an account with that email exists, we&apos;ve sent a password reset link.
          </AlertDescription>
        </Alert>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Email"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            {...register('email')}
          />
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Send Reset Link
          </Button>
        </form>
      )}

      <p className="text-center text-sm text-[var(--text-tertiary)]">
        <Link href="/login" className="text-[var(--accent-500)] hover:text-[var(--accent-600)]">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
