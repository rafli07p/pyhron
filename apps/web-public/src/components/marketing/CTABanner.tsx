'use client';

import { useState } from 'react';
import Link from 'next/link';

export function CTABanner() {
  const [email, setEmail] = useState('');

  return (
    <section className="bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700 py-20">
      <div className="mx-auto max-w-content px-6 text-center">
        <h2 className="font-display text-3xl text-white md:text-4xl">
          Start analyzing IDX equities today
        </h2>
        <p className="mt-4 text-gray-300">
          Free tier includes screener access, 1-year historical data, and 100 API calls per day.
        </p>
        <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            className="w-full max-w-sm rounded-md border border-gray-600 bg-primary-800 px-4 py-3 text-sm text-white placeholder-gray-400 focus:border-accent-500 focus:outline-none"
          />
          <Link
            href="/register"
            className="w-full rounded-md bg-accent-500 px-8 py-3 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors sm:w-auto"
          >
            Request Demo
          </Link>
        </div>
      </div>
    </section>
  );
}
