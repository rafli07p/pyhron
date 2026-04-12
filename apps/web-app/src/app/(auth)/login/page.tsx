'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
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
      setError('Invalid email or password. Please try again.');
    } else {
      router.push('/dashboard');
    }
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden">
      {/* Full-screen background image */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: 'url(/images/login-bg.svg)',
          backgroundColor: '#1a365d',
        }}
      />
      {/* Gradient overlay for readability */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-black/10" />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[440px] rounded-2xl bg-white px-10 py-12 shadow-2xl">
        {/* Logo */}
        <div className="flex justify-center">
          <Image
            src="/logos/logo.svg"
            alt="Pyhron"
            width={160}
            height={44}
            className="h-11 w-auto"
            priority
          />
        </div>

        <h1 className="mt-6 text-center text-[22px] font-semibold text-[#0a0e1a]">
          Sign In
        </h1>

        {reason === 'session_expired' && (
          <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-700">
            Your session has expired. Please sign in again.
          </div>
        )}

        {error && (
          <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-5">
          {/* Email field — MSCI floating label style */}
          <div className="relative">
            <input
              type="email"
              id="email"
              placeholder=" "
              autoComplete="email"
              className="peer w-full rounded-md border border-black/20 bg-white px-4 pb-2.5 pt-5 text-[15px] text-[#0a0e1a] outline-none transition-colors focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
              {...register('email')}
            />
            <label
              htmlFor="email"
              className="pointer-events-none absolute left-4 top-2 text-[11px] text-black/40 transition-all peer-placeholder-shown:top-4 peer-placeholder-shown:text-[14px] peer-focus:top-2 peer-focus:text-[11px] peer-focus:text-[#2563eb]"
            >
              Email address *
            </label>
            {errors.email && <p className="mt-1.5 text-[12px] text-red-500">{errors.email.message}</p>}
          </div>

          {/* Password field */}
          <div className="relative">
            <input
              type="password"
              id="password"
              placeholder=" "
              autoComplete="current-password"
              className="peer w-full rounded-md border border-black/20 bg-white px-4 pb-2.5 pt-5 text-[15px] text-[#0a0e1a] outline-none transition-colors focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
              {...register('password')}
            />
            <label
              htmlFor="password"
              className="pointer-events-none absolute left-4 top-2 text-[11px] text-black/40 transition-all peer-placeholder-shown:top-4 peer-placeholder-shown:text-[14px] peer-focus:top-2 peer-focus:text-[11px] peer-focus:text-[#2563eb]"
            >
              Password *
            </label>
            {errors.password && <p className="mt-1.5 text-[12px] text-red-500">{errors.password.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-[#1a3fd6] py-3.5 text-[15px] font-medium text-white transition-colors hover:bg-[#1530b0] disabled:opacity-50"
          >
            {isSubmitting && <Loader2 size={18} className="animate-spin" />}
            Sign In
          </button>
        </form>

        <p className="mt-6 text-center text-[12px] leading-relaxed text-black/40">
          By clicking &lsquo;Sign In&rsquo; I agree to Pyhron&apos;s{' '}
          <Link href="/legal/terms" className="text-black/60 underline hover:text-black">Terms of Use</Link>
          {' '}below. Don&apos;t have an account?{' '}
          <Link href="/register" className="text-[#1a3fd6] hover:underline">Create an account</Link>
        </p>
      </div>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-8 py-4">
        <span className="text-[11px] text-white/50">&copy; Copyright {new Date().getFullYear()} Pyhron. All rights reserved.</span>
        <div className="flex items-center gap-4">
          <Link href="/legal/terms" className="text-[11px] text-white/50 transition-colors hover:text-white/80">Terms of Use</Link>
          <span className="text-white/20">|</span>
          <Link href="/legal/privacy" className="text-[11px] text-white/50 transition-colors hover:text-white/80">Privacy Notice</Link>
          <span className="text-white/20">|</span>
          <Link href="/contact" className="text-[11px] text-white/50 transition-colors hover:text-white/80">Contact Us</Link>
        </div>
      </div>
    </div>
  );
}
