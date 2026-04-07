'use client';

import { useState } from 'react';

export function CtaBanner() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setSubmitted(true);
  }

  return (
    <section className="bg-[#C9A84C] py-20">
      <div className="mx-auto max-w-2xl px-6 text-center">
        <h2 className="text-3xl font-normal tracking-tight text-[#0A1628] lg:text-4xl">
          Ready to trade with institutional precision?
        </h2>
        <p className="mt-4 text-sm text-[#0A1628]/70">
          Join the waitlist for early access to Pyhron&apos;s research terminal.
        </p>

        {submitted ? (
          <p className="mt-8 text-sm font-medium text-[#0A1628]">
            Thank you. We&apos;ll be in touch.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="mx-auto mt-8 flex max-w-md gap-3">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 border border-[#0A1628]/20 bg-white/80 px-4 py-3 text-sm text-[#1A1A2E] placeholder:text-[#6B7280] focus:border-[#0A1628] focus:outline-none"
              aria-label="Email address"
            />
            <button
              type="submit"
              className="bg-[#0A1628] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[#0F2040]"
            >
              Join Waitlist
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
