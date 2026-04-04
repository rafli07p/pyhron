'use client';

import { useRef } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useWebGLSupport } from '@/hooks/useWebGLSupport';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useHeroAnimation } from '@/hooks/useHeroAnimation';
import { FallbackGradient } from './FallbackGradient';

const DynamicRibbonScene = dynamic(
  () => import('./RibbonScene').then((m) => ({ default: m.RibbonScene })),
  { ssr: false },
);

export function HeroSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const webgl = useWebGLSupport();
  const reduced = useReducedMotion();

  useHeroAnimation(sectionRef);

  const useSmallFallback = typeof window !== 'undefined' && window.innerWidth < 640;

  return (
    <section
      ref={sectionRef}
      className="relative flex h-dvh items-center overflow-hidden bg-[var(--surface-0)]"
    >
      {/* 3D / Fallback layer */}
      <div className="absolute inset-0 z-[1]">
        {reduced ? (
          <FallbackGradient isStatic />
        ) : !webgl || useSmallFallback ? (
          <FallbackGradient />
        ) : (
          <DynamicRibbonScene />
        )}
      </div>

      {/* Content layer */}
      <div className="relative z-[2] flex h-full w-full flex-col justify-center px-6 lg:px-20">
        <div className="max-w-4xl">
          <h1 className="text-5xl font-light leading-[1.05] tracking-tight text-[var(--text-primary)] md:text-7xl lg:text-[5.5rem]">
            <span className="hero-line block">Institutional-Grade</span>
            <span className="hero-line block">Quantitative Research</span>
            <span className="hero-line block">
              for Indonesia&apos;s
            </span>
            <span className="hero-line block">Capital Markets</span>
          </h1>

          <p className="hero-subtext mt-8 max-w-xl text-lg text-[var(--text-secondary)]">
            Pyhron unifies market data, ML-driven signal generation, backtesting, and live
            execution into a single coherent platform.
          </p>

          <div className="hero-cta mt-10 flex gap-4">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-[var(--accent-500)] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
            >
              Start Research
              <span aria-hidden="true">&rarr;</span>
            </Link>
            <Link
              href="/methodology"
              className="inline-flex items-center gap-2 border border-[var(--border-default)] px-6 py-3 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              View Methodology
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="hero-scroll-indicator absolute bottom-8 left-1/2 -translate-x-1/2">
          <div className="h-12 w-px animate-pulse bg-[var(--text-tertiary)]" />
        </div>
      </div>
    </section>
  );
}
