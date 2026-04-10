'use client';

import { useRef, useState, useSyncExternalStore } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { useWebGLSupport } from '@/hooks/useWebGLSupport';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useHeroAnimation } from '@/hooks/useHeroAnimation';
import { FallbackGradient } from './FallbackGradient';

const DynamicRibbonScene = dynamic(
  () => import('./RibbonScene').then((m) => ({ default: m.RibbonScene })),
  { ssr: false },
);

function subSmall(cb: () => void) { window.addEventListener('resize', cb); return () => window.removeEventListener('resize', cb); }
function getSmall() { return window.innerWidth < 640; }
function getSmallServer() { return false; }

export function HeroSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const webgl = useWebGLSupport();
  const reduced = useReducedMotion();
  const isSmall = useSyncExternalStore(subSmall, getSmall, getSmallServer);
  const [threeReady, setThreeReady] = useState(false);

  useHeroAnimation(sectionRef);

  // Hero is always in the initial viewport on the landing page, so there's no
  // reason to gate Three.js loading behind an IntersectionObserver. Computing
  // this from props/state during render (no effect) means the dynamic import
  // kicks off as soon as the component mounts, which removes the flash of the
  // half-painted SVG fallback on refresh.
  const showFallbackOnly = reduced || !webgl || isSmall;
  const loadThreeJs = !showFallbackOnly;

  return (
    <section
      ref={sectionRef}
      className="relative flex min-h-dvh items-center overflow-hidden bg-[#0a0e1a]"
      aria-label="Pyhron — Institutional-grade quantitative research platform for Indonesian capital markets"
    >
      {/* Background layers with crossfade */}
      <div className="absolute inset-0 z-[1]" aria-hidden="true" role="presentation">
        {/* Fallback: always mounts, fades out when Three.js ready */}
        <div
          className="absolute inset-0 transition-opacity duration-500"
          style={{ opacity: threeReady ? 0 : 1, pointerEvents: 'none' }}
        >
          <FallbackGradient isStatic={reduced} />
        </div>

        {/* Three.js: fades in when loaded */}
        {!showFallbackOnly && loadThreeJs && (
          <div
            className="absolute inset-0 transition-opacity duration-500"
            style={{ opacity: threeReady ? 1 : 0 }}
          >
            <DynamicRibbonScene onReady={() => setThreeReady(true)} />
          </div>
        )}
      </div>

      {/* Content layer */}
      <div className="relative z-[2] flex h-full w-full flex-col justify-center px-6 pb-24 pt-32 lg:px-20" role="banner">
        <div className="max-w-4xl">
          <h1 className="text-5xl font-normal leading-[1.05] tracking-tight text-white md:text-7xl lg:text-[5.5rem]">
            <span className="hero-line block">Institutional-Grade</span>
            <span className="hero-line block">Quantitative Research</span>
            <span className="hero-line block">for Indonesia&apos;s</span>
            <span className="hero-line block">Capital Markets</span>
          </h1>

          <p className="hero-subtext mt-8 max-w-xl text-lg text-white/75">
            Pyhron unifies market data, ML-driven signal generation, backtesting, and live
            execution into a single coherent platform.
          </p>

          <div className="hero-cta mt-10 flex flex-col items-start gap-4">
            <div className="flex gap-4">
              <Link
                href="/register"
                className="group inline-flex items-center gap-2 rounded-lg bg-[var(--accent-500)] px-8 py-4 text-base font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
              >
                Get Started Free
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href="/dashboard"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-8 py-4 text-base font-medium text-white/80 transition-colors hover:border-white/30 hover:text-white"
              >
                Launch Terminal
              </a>
            </div>
            <p className="text-sm text-white/50">Free Explorer tier — no credit card required</p>
          </div>
        </div>
      </div>
    </section>
  );
}
