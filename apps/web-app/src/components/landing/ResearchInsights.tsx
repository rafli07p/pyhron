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
    // Light-gray tint differentiates this section from the white
    // FeaturedSolutions above it — matches MSCI's alternating section rhythm.
    <section className="bg-[#f4f5f7] py-16 lg:py-20">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-12">
        {/* Header */}
        <ScrollReveal>
          <h2
            className="font-semibold leading-[1.1]"
            style={{
              color: MSCI_BRAND_BLUE,
              fontSize: '2.25rem',
              letterSpacing: '-0.04em',
            }}
          >
            Research &amp; Insights
          </h2>
          <p
            className="mt-2 font-semibold leading-[1.1]"
            style={{
              color: '#6a7cfb',
              fontSize: '2.25rem',
              letterSpacing: '-0.04em',
            }}
          >
            Stay ahead of changing markets
          </p>

          <Link
            href="/research/quant"
            className="mt-8 inline-flex h-12 items-center gap-2 rounded-full px-8 text-[14px] font-medium text-white transition-opacity hover:opacity-90"
            style={{ backgroundColor: MSCI_BRAND_BLUE }}
          >
            Explore all research
          </Link>
        </ScrollReveal>

        {/* Card grid — tight 6px gap matching MSCI */}
        <div className="mt-14 grid grid-cols-1 gap-[6px] lg:grid-cols-[1fr_1fr] lg:grid-rows-[1fr_1fr]">
          {/* White "cover" card spanning both rows — sits on the gray
              section background for clear separation. */}
          <Link
            href="/research/quant"
            className="group relative overflow-hidden rounded-2xl bg-white p-8 transition-transform duration-300 ease-out hover:-translate-y-1 lg:row-span-2"
          >
            <div className="pointer-events-none flex h-[340px] items-center justify-center lg:h-[380px]">
              <SphereVisual />
            </div>
            <div className="relative mt-6 max-w-[88%]">
              <h3 className="font-semibold leading-[1.25] tracking-tight text-black" style={{ fontSize: '1.5rem', letterSpacing: '-0.02em' }}>
                IDX Factor Models Under Stress
              </h3>
              <p className="mt-3 font-normal text-black/70" style={{ fontSize: '0.95rem', lineHeight: 1.45 }}>
                The AI-driven equity rotation that rattled developed markets earlier this
                year also exposed a fault line in IDX factor premia. We examine the
                implications for Indonesia-focused quant portfolios.
              </p>
            </div>
            <span className="mt-6 inline-flex h-10 w-fit items-center gap-2 rounded-full border border-black/60 px-5 text-[13px] font-medium text-black transition-colors group-hover:border-black">
              Read more
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>

          {/* Black card */}
          <Link
            href="/research/ml"
            className="group relative overflow-hidden rounded-2xl bg-[#0a0e1a] p-8 transition-transform duration-300 ease-out hover:-translate-y-1"
          >
            <MosaicVisual className="absolute right-0 top-0 h-full w-[55%]" tone="warm" />
            <div className="relative max-w-[55%]">
              <h3 className="font-semibold leading-[1.25] tracking-tight text-white" style={{ fontSize: '1.4rem', letterSpacing: '-0.02em' }}>
                US–China tensions reshape IDX foreign flows
              </h3>
              <p className="mt-3 font-normal text-white/70" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                It may be time to reassess currency-hedged exposure as portfolio
                reallocations flip historical beta relationships across Indonesian
                equities.
              </p>
            </div>
            <span className="relative mt-6 inline-flex h-10 w-fit items-center gap-2 rounded-full border border-white/60 px-5 text-[13px] font-medium text-white transition-colors group-hover:border-white">
              Learn more
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>

          {/* Blue card */}
          <Link
            href="/research/risk"
            className="group relative overflow-hidden rounded-2xl p-8 transition-transform duration-300 ease-out hover:-translate-y-1"
            style={{ backgroundColor: MSCI_BRAND_BLUE }}
          >
            <MosaicVisual className="absolute right-0 top-0 h-full w-[55%]" tone="cool" />
            <div className="relative max-w-[55%]">
              <h3 className="font-semibold leading-[1.25] tracking-tight text-white" style={{ fontSize: '1.4rem', letterSpacing: '-0.02em' }}>
                IDX Liquidity Premium
              </h3>
              <p className="mt-3 font-normal text-white/80" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                Could volatility measures signal a coming dislocation in second-board
                Indonesian equities?
              </p>
            </div>
            <span className="relative mt-6 inline-flex h-10 w-fit items-center gap-2 rounded-full border border-white/80 px-5 text-[13px] font-medium text-white transition-colors group-hover:border-white">
              Get the facts
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
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
