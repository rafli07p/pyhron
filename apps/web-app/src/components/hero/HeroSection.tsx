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
      {/* Background — visible flowing gradient like MSCI */}
      <div className="absolute inset-0 z-[1]" aria-hidden="true" role="presentation">
        <div className="absolute inset-0 bg-[#f0f4ff]" />

        {/* Large flowing blobs — clearly visible */}
        <div
          className="absolute -right-[5%] -top-[10%] h-[80%] w-[70%] rounded-full"
          style={{
            background: 'radial-gradient(ellipse, rgba(59,130,246,0.18), transparent 65%)',
            animation: reduced ? 'none' : 'hero-drift-1 20s ease-in-out infinite',
          }}
        />
        <div
          className="absolute -left-[10%] bottom-[0%] h-[60%] w-[60%] rounded-full"
          style={{
            background: 'radial-gradient(ellipse, rgba(139,92,246,0.14), transparent 65%)',
            animation: reduced ? 'none' : 'hero-drift-2 25s ease-in-out infinite',
          }}
        />
        <div
          className="absolute left-[25%] top-[30%] h-[50%] w-[50%] rounded-full"
          style={{
            background: 'radial-gradient(ellipse, rgba(6,182,212,0.12), transparent 65%)',
            animation: reduced ? 'none' : 'hero-drift-3 18s ease-in-out infinite',
          }}
        />
        <div
          className="absolute right-[10%] bottom-[10%] h-[45%] w-[45%] rounded-full"
          style={{
            background: 'radial-gradient(ellipse, rgba(37,99,235,0.10), transparent 60%)',
            animation: reduced ? 'none' : 'hero-drift-4 22s ease-in-out infinite',
          }}
        />

        <style>{`
          @keyframes hero-drift-1 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(-4%, 6%) scale(1.08); }
            66% { transform: translate(3%, -4%) scale(0.94); }
          }
          @keyframes hero-drift-2 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(5%, -4%) scale(1.1); }
            66% { transform: translate(-3%, 5%) scale(0.95); }
          }
          @keyframes hero-drift-3 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(-6%, 4%) scale(1.12); }
          }
          @keyframes hero-drift-4 {
            0%, 100% { transform: translate(0, 0) scale(1); }
            40% { transform: translate(4%, 3%) scale(1.06); }
            70% { transform: translate(-3%, -5%) scale(0.97); }
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
