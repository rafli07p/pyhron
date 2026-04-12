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
      aria-label="Pyhron — powering better investment decisions for Indonesian capital markets"
    >
      <div className="absolute inset-0 z-[1]" aria-hidden="true" role="presentation">
        <FallbackGradient isStatic={reduced} />
      </div>

      <div className="relative z-[2] mx-auto flex h-full w-full max-w-[1400px] flex-col justify-center px-6 pb-24 pt-32 lg:px-8" role="banner">
        <div className="max-w-3xl">
          <h1 className="text-5xl font-normal leading-[1.05] tracking-tight text-[#0a0e1a] md:text-7xl lg:text-[5.5rem]">
            <span className="hero-line block">Powering better</span>
            <span className="hero-line block">investment decisions</span>
            <span className="hero-line block">for Indonesian</span>
            <span className="hero-line block">capital markets</span>
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
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 rounded-lg border border-black/15 px-8 py-4 text-base font-medium text-black/70 transition-colors hover:border-black/30 hover:text-black"
              >
                Schedule Demo
              </Link>
            </div>
            <p className="text-sm text-black/40">Free Explorer tier — no credit card required</p>
          </div>
        </div>
      </div>
    </section>
  );
}
