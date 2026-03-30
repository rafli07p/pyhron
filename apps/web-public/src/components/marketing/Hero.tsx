'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

function AnimatedCounter({ end, label, duration = 1500 }: { end: number; label: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
        }
      },
      { threshold: 0.5 },
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started) return;
    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(easeOut * end));
      if (progress >= 1) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [started, end, duration]);

  return (
    <div ref={ref} className="text-center">
      <div className="font-display text-4xl md:text-5xl text-white">{count.toLocaleString()}+</div>
      <div className="mt-2 text-sm text-gray-400">{label}</div>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-[#0a0e1a]">
      <div
        className="absolute inset-0 animate-mesh-drift"
        style={{
          background: [
            'radial-gradient(ellipse at 30% 50%, rgba(0,212,170,0.2) 0%, transparent 60%)',
            'radial-gradient(ellipse at 70% 50%, rgba(26,58,107,0.3) 0%, transparent 60%)',
          ].join(', '),
        }}
      />
      <div className="relative mx-auto max-w-content px-6 py-24 md:py-32 lg:py-40">
        <div className="max-w-3xl">
          <h1 className="font-display text-4xl leading-tight text-white md:text-5xl lg:text-6xl">
            Quantitative Analytics and Trading for IDX
          </h1>
          <p className="mt-6 text-lg text-gray-300 md:text-xl">
            Factor models, backtesting, and live execution for IDX equities.
            500+ factor signals across 50+ stocks.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/register"
              className="rounded-md bg-accent-500 px-8 py-3 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
            >
              Get Started Free
            </Link>
            <Link
              href="/pricing"
              className="rounded-md border border-gray-600 px-8 py-3 text-sm font-medium text-white hover:border-gray-400 transition-colors"
            >
              View Pricing
            </Link>
          </div>
        </div>
        <div className="mt-20 grid grid-cols-2 gap-8 md:grid-cols-4">
          <AnimatedCounter end={500} label="Factor Signals" />
          <AnimatedCounter end={50} label="IDX Stocks Covered" />
          <AnimatedCounter end={10} label="Years of Historical Data" />
          <AnimatedCounter end={5} label="Trading Strategies" />
        </div>
      </div>
    </section>
  );
}
