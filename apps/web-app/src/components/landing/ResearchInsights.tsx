'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { ScrollReveal } from '@/components/motion/ScrollReveal';

/**
 * Research & Insights — MSCI-style editorial section that pairs a 2-line
 * blue headline + a "Explore all research" pill CTA with an asymmetric
 * 2-column card grid:
 *
 *   ┌──────────────────┬──────────────┐
 *   │                  │   black card │
 *   │   light tall     ├──────────────┤
 *   │   "cover" card   │   blue card  │
 *   └──────────────────┴──────────────┘
 *
 * Each card links to an existing research route; swap the hrefs when the
 * real article destinations are ready.
 */

const MSCI_BRAND_BLUE = '#1a3fd6';

export function ResearchInsights() {
  return (
    <section className="bg-[#f5f5f7] py-20 lg:py-28">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-8">
        {/* Header — MSCI ms-headline1: 2.25rem mobile → 4rem desktop */}
        <ScrollReveal>
          <h2
            className="font-semibold leading-[1.1] text-[2.25rem] lg:text-[4rem]"
            style={{ color: MSCI_BRAND_BLUE, letterSpacing: '-0.06em' }}
          >
            Research &amp; Insights
          </h2>
          <p
            className="font-semibold leading-[1.1] text-[2.25rem] lg:text-[4rem]"
            style={{ color: '#6a7cfb', letterSpacing: '-0.06em' }}
          >
            Stay ahead of changing markets
          </p>

          <Link
            href="/research-and-insights"
            className="mt-8 inline-flex h-13 items-center gap-2 rounded-full px-9 text-[15px] font-medium text-white transition-opacity hover:opacity-90"
            style={{ backgroundColor: MSCI_BRAND_BLUE }}
          >
            Explore all research
          </Link>
        </ScrollReveal>

        {/* Card grid — MSCI: ~10px gaps, rounded-lg */}
        <div className="mt-12 grid grid-cols-1 gap-2.5 lg:grid-cols-[1.15fr_1fr] lg:grid-rows-[1fr_1fr]">
          {/* Gray "cover" card spanning both rows */}
          <div
            className="group relative overflow-hidden rounded-2xl bg-white p-8 lg:row-span-2 lg:min-h-[560px]"
          >
            <div className="pointer-events-none flex h-[300px] items-center justify-center lg:h-[340px]">
              <SphereVisual />
            </div>
            <div className="relative mt-4 max-w-[90%]">
              <h3 className="text-[1.5rem] font-semibold leading-[1.25] tracking-tight text-black lg:text-[1.75rem]" style={{ letterSpacing: '-0.02em' }}>
                IDX Factor Models Under Stress
              </h3>
              <p className="mt-3 text-[1rem] font-normal leading-[1.55] text-black/60">
                The AI-driven equity rotation that rattled developed markets earlier this
                year also exposed a fault line in IDX factor premia. We examine the
                implications for Indonesia-focused quant portfolios.
              </p>
            </div>
            <Link href="/research-and-insights/articles/idx-factor-stress-test" className="mt-6 inline-flex h-12 w-fit items-center gap-2 rounded-full border border-black/50 px-7 text-[15px] font-medium text-black transition-colors hover:border-black">
              Read more
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Black card */}
          <div
            className="group relative overflow-hidden rounded-2xl bg-[#0a0e1a] p-8 lg:min-h-[270px]"
          >
            <MosaicVisual className="absolute right-0 top-0 h-full w-[55%]" tone="warm" />
            <div className="relative max-w-[55%]">
              <h3 className="text-[1.375rem] font-semibold leading-[1.25] tracking-tight text-white lg:text-[1.625rem]" style={{ letterSpacing: '-0.02em' }}>
                US–China tensions reshape IDX foreign flows
              </h3>
              <p className="mt-3 text-[1rem] font-normal leading-[1.5] text-white/70">
                It may be time to reassess currency-hedged exposure as portfolio
                reallocations flip historical beta relationships across Indonesian
                equities.
              </p>
            </div>
            <Link href="/research-and-insights/articles/us-china-idx-flows" className="relative mt-6 inline-flex h-12 w-fit items-center gap-2 rounded-full border border-white/50 px-7 text-[15px] font-medium text-white transition-colors hover:border-white">
              Learn more
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Blue card */}
          <div
            className="group relative overflow-hidden rounded-2xl p-8 lg:min-h-[270px]"
            style={{ backgroundColor: MSCI_BRAND_BLUE }}
          >
            <MosaicVisual className="absolute right-0 top-0 h-full w-[55%]" tone="cool" />
            <div className="relative max-w-[55%]">
              <h3 className="text-[1.375rem] font-semibold leading-[1.25] tracking-tight text-white lg:text-[1.625rem]" style={{ letterSpacing: '-0.02em' }}>
                IDX Liquidity Premium
              </h3>
              <p className="mt-3 text-[1rem] font-normal leading-[1.5] text-white/80">
                Could volatility measures signal a coming dislocation in second-board
                Indonesian equities?
              </p>
            </div>
            <Link href="/research-and-insights/articles/idx-liquidity-premium" className="relative mt-6 inline-flex h-12 w-fit items-center gap-2 rounded-full border border-white/70 px-7 text-[15px] font-medium text-white transition-colors hover:border-white">
              Get the facts
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Visual primitives ────────────────────────────────────────────────────

function SphereVisual() {
  return (
    <svg viewBox="0 0 400 400" className="h-full w-full max-w-[380px]" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="sphere-body" cx="35%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#93c5fd" />
          <stop offset="45%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#0c1f5c" />
        </radialGradient>
        <pattern id="sphere-scale" x="0" y="0" width="14" height="18" patternUnits="userSpaceOnUse">
          <path d="M7 0 C 11 6, 11 12, 7 18 C 3 12, 3 6, 7 0 Z" fill="rgba(255,255,255,0.18)" stroke="rgba(255,255,255,0.25)" strokeWidth="0.5" />
        </pattern>
      </defs>
      <circle cx="170" cy="200" r="130" fill="url(#sphere-body)" />
      <circle cx="170" cy="200" r="130" fill="url(#sphere-scale)" opacity="0.8" />
      {/* orbit rings */}
      {[150, 175, 200].map((r) => (
        <ellipse
          key={r}
          cx="220"
          cy="200"
          rx={r}
          ry={r * 0.55}
          fill="none"
          stroke="#14b8a6"
          strokeOpacity={0.55 - (r - 150) * 0.005}
          strokeWidth="1.5"
        />
      ))}
      <circle cx="360" cy="200" r="5" fill="#14b8a6" />
    </svg>
  );
}

function MosaicVisual({ className, tone }: { className?: string; tone: 'warm' | 'cool' }) {
  const fills =
    tone === 'warm'
      ? ['#92400e', '#b45309', '#d97706', '#f59e0b', '#78350f', '#451a03']
      : ['#dbeafe', '#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6', '#1d4ed8'];

  return (
    <svg viewBox="0 0 400 500" className={className} preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      {/* radial tile pattern */}
      {Array.from({ length: 18 }).map((_, ring) =>
        Array.from({ length: 16 }).map((_, seg) => {
          const angle = (seg / 16) * Math.PI * 2;
          const radius = 30 + ring * 22;
          const cx = 260 + Math.cos(angle) * radius;
          const cy = 250 + Math.sin(angle) * radius;
          const fill = fills[(ring + seg) % fills.length];
          return (
            <circle
              key={`${ring}-${seg}`}
              cx={cx}
              cy={cy}
              r={6 + (ring % 3)}
              fill={fill}
              opacity={0.15 + (ring % 4) * 0.15}
            />
          );
        }),
      )}
    </svg>
  );
}
