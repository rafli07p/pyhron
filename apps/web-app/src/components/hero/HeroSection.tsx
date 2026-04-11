'use client';

import { useRef } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useHeroAnimation } from '@/hooks/useHeroAnimation';
import { FallbackGradient } from './FallbackGradient';

export function HeroSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();

  useHeroAnimation(sectionRef);

  return (
    <section
      ref={sectionRef}
      className="relative flex min-h-dvh items-center overflow-hidden bg-white"
      aria-label="Pyhron — Institutional-grade quantitative research platform for Indonesian capital markets"
    >
      {/* Dominant white background with the cycling ribbon animation. */}
      <div className="absolute inset-0 z-[1]" aria-hidden="true" role="presentation">
        <FallbackGradient isStatic={reduced} />
      </div>

      {/* Content layer */}
      <div className="relative z-[2] flex h-full w-full flex-col justify-center px-6 pb-24 pt-32 lg:px-20" role="banner">
        <div className="max-w-4xl">
          <h1 className="text-5xl font-normal leading-[1.05] tracking-tight text-[#0a0e1a] md:text-7xl lg:text-[5.5rem]">
            <span className="hero-line block">Institutional-Grade</span>
            <span className="hero-line block">Quantitative Research</span>
            <span className="hero-line block">for Indonesia&apos;s</span>
            <span className="hero-line block">Capital Markets</span>
          </h1>

          <p className="hero-subtext mt-8 max-w-xl text-lg text-black/65">
            Pyhron unifies market data, ML-driven signal generation, backtesting, and live
            execution into a single coherent platform.
          </p>

          <div className="hero-cta mt-10 flex flex-col items-start gap-4">
            <div className="flex gap-4">
              <Link
                href="/register"
                className="group inline-flex items-center gap-2 rounded-lg bg-[#2563eb] px-8 py-4 text-base font-medium text-white transition-colors hover:bg-[#1d4ed8]"
              >
                Get Started Free
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href="/dashboard"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-black/15 px-8 py-4 text-base font-medium text-black/70 transition-colors hover:border-black/30 hover:text-black"
              >
                Launch Terminal
              </a>
            </div>
            <p className="text-sm text-black/40">Free Explorer tier — no credit card required</p>
          </div>
        </div>
      </div>
    </section>
  );
}
