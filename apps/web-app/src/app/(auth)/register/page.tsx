'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, Check } from 'lucide-react';

const step1Schema = z.object({
  email: z.string().email('Please enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  tos: z.literal(true, 'You must accept the terms'),
}).refine((d) => d.password === d.confirmPassword, { message: 'Passwords do not match', path: ['confirmPassword'] });

type Step1 = z.infer<typeof step1Schema>;

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

const steps = ['Account', 'Profile', 'Plan'];

const inputClass =
  'w-full bg-[#0f0f12] border border-white/[0.08] focus:border-[var(--accent-500)] focus:outline-none rounded-lg px-4 py-3 text-sm text-white placeholder:text-white/20 transition-colors';
const selectClass =
  'w-full bg-[#0f0f12] border border-white/[0.08] focus:border-[var(--accent-500)] focus:outline-none rounded-lg px-4 py-3 text-sm text-white transition-colors appearance-none';
const btnPrimary =
  'flex items-center justify-center gap-2 rounded-lg bg-[var(--accent-500)] px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)] disabled:opacity-50';
const btnSecondary =
  'rounded-lg border border-white/[0.08] px-4 py-3 text-sm font-medium text-white/60 transition-colors hover:text-white hover:border-white/20';

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [account, setAccount] = useState({ email: '', password: '', confirmPassword: '' });
  const [profile, setProfile] = useState({ fullName: '', institution: '', experience: '' });

  const form1 = useForm<Step1>({ resolver: zodResolver(step1Schema) });

  const handleStep1 = form1.handleSubmit((data) => {
    setAccount({ email: data.email, password: data.password, confirmPassword: data.confirmPassword });
    setStep(2);
  });

  const handleStep2 = () => {
    if (!profile.fullName.trim()) return;
    setStep(3);
  };

  const handleFinish = async (plan: string) => {
    setLoading(true);
    try {
      await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...account, ...profile, plan }),
      });
    } catch { /* proceed anyway */ }
    router.push('/login?registered=true');
  };

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-[#0a0a0c] px-4">
      <DiamondPattern />
      <div className="fixed top-0 left-0 right-0 flex items-center px-6 py-4 z-10">
        <Link href="/" className="text-xs font-semibold tracking-[0.3em] text-white/70 uppercase">Pyhron</Link>
      </div>

      <div className="relative z-10 w-full max-w-[480px] rounded-xl border border-white/[0.06] bg-[#18181b]/90 p-8 shadow-2xl">
        {/* Step indicator */}
        <div className="mb-6 flex items-center justify-between">
          {steps.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                i + 1 < step ? 'bg-[var(--accent-500)] text-white' : i + 1 === step ? 'bg-white/10 text-white' : 'bg-white/5 text-white/30'
              }`}>
                {i + 1 < step ? <Check size={12} /> : i + 1}
              </div>
              <span className={`text-xs ${i + 1 <= step ? 'text-white/70' : 'text-white/30'}`}>{label}</span>
              {i < 2 && <div className={`mx-2 h-px w-8 ${i + 1 < step ? 'bg-[var(--accent-500)]' : 'bg-white/10'}`} />}
            </div>
          ))}
        </div>

        {/* Step 1 */}
        {step === 1 && (
          <form onSubmit={handleStep1} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Email</label>
              <input type="email" placeholder="you@example.com" className={inputClass} {...form1.register('email')} />
              {form1.formState.errors.email && <p className="mt-1 text-xs text-red-400">{form1.formState.errors.email.message}</p>}
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Password</label>
              <input type="password" placeholder="Min 8 characters" className={inputClass} {...form1.register('password')} />
              {form1.formState.errors.password && <p className="mt-1 text-xs text-red-400">{form1.formState.errors.password.message}</p>}
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Confirm Password</label>
              <input type="password" placeholder="••••••••" className={inputClass} {...form1.register('confirmPassword')} />
              {form1.formState.errors.confirmPassword && <p className="mt-1 text-xs text-red-400">{form1.formState.errors.confirmPassword.message}</p>}
            </div>
            <label className="flex items-start gap-2 text-xs text-white/40">
              <input type="checkbox" className="mt-0.5 accent-[var(--accent-500)]" {...form1.register('tos')} />
              <span>I agree to the <Link href="/terms" className="text-[var(--accent-500)]">Terms of Service</Link> and <Link href="/privacy" className="text-[var(--accent-500)]">Privacy Policy</Link></span>
            </label>
            {form1.formState.errors.tos && <p className="text-xs text-red-400">{form1.formState.errors.tos.message}</p>}
            <button type="submit" className={`w-full ${btnPrimary}`}>Next</button>
          </form>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Full Name</label>
              <input value={profile.fullName} onChange={(e) => setProfile({ ...profile, fullName: e.target.value })} placeholder="John Doe" className={inputClass} />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Institution Type</label>
              <select value={profile.institution} onChange={(e) => setProfile({ ...profile, institution: e.target.value })} className={selectClass}>
                <option value="">Select...</option>
                <option value="individual">Individual</option>
                <option value="fund">Fund</option>
                <option value="prop">Prop Firm</option>
                <option value="corporate">Corporate</option>
                <option value="academic">Academic</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Trading Experience</label>
              <select value={profile.experience} onChange={(e) => setProfile({ ...profile, experience: e.target.value })} className={selectClass}>
                <option value="">Select...</option>
                <option value="<1">Less than 1 year</option>
                <option value="1-3">1-3 years</option>
                <option value="3-5">3-5 years</option>
                <option value="5+">5+ years</option>
              </select>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className={btnSecondary}>Back</button>
              <button onClick={handleStep2} disabled={!profile.fullName.trim()} className={`flex-1 ${btnPrimary}`}>Next</button>
            </div>
          </div>
        )}

        {/* Step 3 */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-white/[0.08] p-4 hover:border-white/20 transition-colors">
                <h3 className="text-sm font-medium text-white">Explorer</h3>
                <p className="text-xs text-white/30">Free</p>
                <p className="mt-2 text-xs text-white/50">Watch &amp; Learn</p>
                <ul className="mt-3 space-y-1 text-xs text-white/40">
                  <li>Market data access</li>
                  <li>Community strategies</li>
                  <li>Basic charting</li>
                </ul>
                <button onClick={() => handleFinish('explorer')} disabled={loading} className={`mt-4 w-full ${btnPrimary} text-xs`}>
                  {loading ? <Loader2 size={14} className="animate-spin" /> : 'Get Started Free'}
                </button>
              </div>
              <div className="rounded-lg border border-[var(--accent-500)]/30 bg-[var(--accent-500)]/5 p-4">
                <h3 className="text-sm font-medium text-white">Strategist</h3>
                <p className="text-xs text-[var(--accent-400)]">14-day trial</p>
                <p className="mt-2 text-xs text-white/50">Build &amp; Test</p>
                <ul className="mt-3 space-y-1 text-xs text-white/40">
                  <li>Strategy builder</li>
                  <li>Backtesting engine</li>
                  <li>Risk analytics</li>
                </ul>
                <button onClick={() => handleFinish('strategist')} disabled={loading} className={`mt-4 w-full ${btnPrimary} text-xs`}>
                  {loading ? <Loader2 size={14} className="animate-spin" /> : 'Start Free Trial'}
                </button>
              </div>
            </div>
            <button onClick={() => setStep(2)} className={btnSecondary}>Back</button>
          </div>
        )}

        <p className="mt-6 text-center text-sm text-white/40">
          Already have an account?{' '}
          <Link href="/login" className="text-[var(--accent-500)] hover:text-[var(--accent-400)]">Sign in</Link>
        </p>
      </div>
      <Footer />
    </div>
  );
}
