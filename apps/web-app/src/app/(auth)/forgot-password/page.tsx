'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';

const schema = z.object({
  email: z.string().email('Please enter a valid email'),
});

type ResetForm = z.infer<typeof schema>;

const DiamondPattern = () => (
  <svg className="absolute inset-0 h-full w-full opacity-[0.04]" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <pattern id="diamonds" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M20 0L40 20L20 40L0 20Z" fill="none" stroke="white" strokeWidth="0.5" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#diamonds)" />
  </svg>
);

const Footer = () => (
  <div className="fixed bottom-0 left-0 right-0 flex items-center justify-center gap-4 py-4 text-[10px] text-white/15">
    <span>&copy; {new Date().getFullYear()} Pyhron</span>
    <Link href="/contact" className="hover:text-white/30 transition-colors">Contact Us</Link>
    <Link href="/terms" className="hover:text-white/30 transition-colors">Terms</Link>
    <Link href="/privacy" className="hover:text-white/30 transition-colors">Privacy</Link>
  </div>
);

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ResetForm>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async () => {
    await new Promise((r) => setTimeout(r, 800));
    setSent(true);
  };

  const inputClass =
    'w-full bg-[#0f0f12] border border-white/[0.08] focus:border-[var(--accent-500)] focus:outline-none rounded-lg px-4 py-3 text-sm text-white placeholder:text-white/20 transition-colors';

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-[#0a0a0c] px-4">
      <DiamondPattern />
      <div className="fixed top-0 left-0 right-0 flex items-center px-6 py-4 z-10">
        <Link href="/" className="text-xs font-semibold tracking-[0.3em] text-white/70 uppercase">Pyhron</Link>
      </div>

      <div className="relative z-10 w-full max-w-[420px] rounded-xl border border-white/[0.06] bg-[#18181b]/90 p-8 shadow-2xl">
        <h1 className="text-2xl font-normal text-white">Reset your password</h1>
        <p className="mt-1 text-sm text-white/40">Enter your email and we&apos;ll send you a reset link.</p>

        {sent ? (
          <div className="mt-6 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-sm text-emerald-300">
            If an account exists with that email, you&apos;ll receive a reset link shortly.
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Email</label>
              <input type="email" placeholder="you@example.com" autoComplete="email" className={inputClass} {...register('email')} />
              {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent-500)] px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)] disabled:opacity-50"
            >
              {isSubmitting && <Loader2 size={16} className="animate-spin" />}
              Send Reset Link
            </button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-white/40">
          Remember your password?{' '}
          <Link href="/login" className="text-[var(--accent-500)] hover:text-[var(--accent-400)]">Log in</Link>
        </p>
      </div>
      <Footer />
    </div>
  );
}
