'use client';

import { useRef } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useHeroAnimation } from '@/hooks/useHeroAnimation';

export function HeroSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();

  useHeroAnimation(sectionRef);

  return (
    <section
      ref={sectionRef}
      className="relative flex min-h-dvh items-end overflow-hidden bg-white"
      aria-label="Pyhron — powering better investment decisions"
    >
      {/* Smooth animated gradient background */}
      <div className="absolute inset-0 z-[1]" aria-hidden="true" role="presentation">
        <div className="absolute inset-0 bg-white" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(37,99,235,0.06),transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(139,92,246,0.04),transparent_55%)]" />

        {/* Smooth flowing gradient blobs */}
        <div
          className="absolute -right-[10%] top-[15%] h-[70%] w-[65%] rounded-full opacity-[0.12]"
          style={{
            background: 'radial-gradient(ellipse, #3b82f6, transparent 70%)',
            animation: reduced ? 'none' : 'hero-drift-1 20s ease-in-out infinite',
          }}
        />
        <div
          className="absolute -left-[5%] bottom-[5%] h-[50%] w-[55%] rounded-full opacity-[0.08]"
          style={{
            background: 'radial-gradient(ellipse, #8b5cf6, transparent 70%)',
            animation: reduced ? 'none' : 'hero-drift-2 25s ease-in-out infinite',
          }}
        />
        <div
          className="absolute left-[30%] top-[40%] h-[40%] w-[40%] rounded-full opacity-[0.06]"
          style={{
            background: 'radial-gradient(ellipse, #06b6d4, transparent 70%)',
            animation: reduced ? 'none' : 'hero-drift-3 18s ease-in-out infinite',
          }}
        />

        <style>{`
          @keyframes hero-drift-1 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(-3%, 5%) scale(1.05); }
            66% { transform: translate(2%, -3%) scale(0.95); }
          }
          @keyframes hero-drift-2 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(4%, -3%) scale(1.08); }
            66% { transform: translate(-2%, 4%) scale(0.96); }
          }
          @keyframes hero-drift-3 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(-5%, 3%) scale(1.1); }
          }
        `}</style>
      </div>

      <div className="relative z-[2] mx-auto flex w-full max-w-[1400px] flex-col justify-end px-6 pb-[12vh] pt-[200px] lg:px-8" role="banner">
        <div className="max-w-3xl">
          <h1 className="text-5xl font-normal leading-[1.05] tracking-tight text-[#0a0e1a] md:text-7xl lg:text-[5.5rem]">
            <span className="hero-line block">Powering better</span>
            <span className="hero-line block">investment</span>
            <span className="hero-line block">decisions</span>
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
