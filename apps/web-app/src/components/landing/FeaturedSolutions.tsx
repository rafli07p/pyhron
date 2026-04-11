'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { ScrollReveal } from '@/components/motion/ScrollReveal';

// MSCI brand blue, pulled directly from their `.ms-text-brandblue-700` class.
const MSCI_BRAND_BLUE = '#1a3fd6';

/**
 * Featured Solutions — MSCI-style section that pairs a 3-column intro with
 * an asymmetric 2-column card grid of clickable deep-links.
 *
 * Layout at `lg` breakpoint:
 *
 *   ┌──────────────────┬────────────┐
 *   │                  │   small A  │
 *   │   big hero       ├────────────┤
 *   │                  │   small B  │
 *   ├──────────────────┼────────────┤
 *   │    small C       │   small D  │
 *   └──────────────────┴────────────┘
 *
 * Each card is wrapped in a <Link> so the entire tile is clickable; hrefs
 * intentionally point at existing routes (methodology / research / etc) as
 * placeholders — update them when the real destinations exist.
 */

const introColumns = [
  {
    title: 'Data & Analytics',
    desc:
      'Integrated view of risk and return across IDX instruments to help you identify and size opportunities with confidence.',
  },
  {
    title: 'Public & Private Indexes',
    desc:
      'A suite of indexes built to accurately represent and measure Indonesian public and private markets.',
  },
  {
    title: 'Research & Insights',
    desc:
      'Explore insights and analysis on key topics across asset classes, market themes, risk and more.',
  },
];

export function FeaturedSolutions() {
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-[1200px] px-6 lg:px-8">
        {/* Header — both lines styled with MSCI's `ms-headline1-sm` scale
            (2.25rem / 1.1 / -0.04em tracking) and `ms-text-brandblue-700`. */}
        <ScrollReveal>
          <h2
            className="font-semibold leading-[1.1]"
            style={{
              color: MSCI_BRAND_BLUE,
              fontSize: '2.25rem',
              letterSpacing: '-0.04em',
            }}
          >
            Featured solutions
          </h2>
          <p
            className="mt-2 font-semibold leading-[1.1]"
            style={{
              color: MSCI_BRAND_BLUE,
              fontSize: '2.25rem',
              letterSpacing: '-0.04em',
            }}
          >
            End-to-end tools to meet your needs
          </p>
        </ScrollReveal>

        {/* Intro columns — plain text blocks (no link arrow, no hover color
            shift). Titles use `ms-font-semibold ms-text-black`, bodies use
            `ms-font-regular ms-body-l-sm ms-text-black`. */}
        <ScrollReveal preset="fadeUp" stagger={0.12} className="mt-12 grid grid-cols-1 gap-10 md:grid-cols-3">
          {introColumns.map((col) => (
            <div key={col.title}>
              <h3 className="font-semibold text-black" style={{ fontSize: '1rem', lineHeight: 1.4, letterSpacing: '-0.01em' }}>
                {col.title}
              </h3>
              <p className="mt-3 font-normal text-black" style={{ fontSize: '1rem', lineHeight: 1.4, letterSpacing: '-0.01em' }}>
                {col.desc}
              </p>
            </div>
          ))}
        </ScrollReveal>

        {/* Card grid */}
        <div className="mt-16 grid grid-cols-1 gap-4 lg:grid-cols-2 lg:grid-rows-[auto_auto_auto]">
          {/* Big hero card — spans 2 rows on lg */}
          <Card
            href="/data/ml-signals"
            className="lg:row-span-2"
            tone="indigo"
            heightClass="min-h-[380px] lg:min-h-[560px]"
            visual={<VisualOrbits />}
            title="Pyhron adds ML-driven alpha to IDX research"
            desc="Expanding systematic capabilities across the Indonesian capital markets research lifecycle."
            cta="Explore ML for quant research"
            variant="light-on-dark"
          />

          {/* Small card A — light / gray */}
          <Card
            href="/data/factors"
            tone="white"
            heightClass="min-h-[260px]"
            visual={<VisualBars />}
            title="Enhancing our multi-asset factor analytics"
            kicker="Pyhron extends Fama-French five-factor coverage"
            cta="Read the news"
            variant="dark-on-light"
          />

          {/* Small card B — teal */}
          <Card
            href="/research/quant"
            tone="teal"
            heightClass="min-h-[260px]"
            visual={<VisualWaves />}
            title="Daily IDX factor exposures are here"
            desc="Nowcasting delivers decision-grade signals between reporting periods."
            cta="See how it works"
            variant="dark-on-light"
          />

          {/* Small card C — black with "photo" placeholder */}
          <Card
            href="/markets"
            tone="black"
            heightClass="min-h-[260px]"
            visual={<VisualLines />}
            title="Explore the new Markets in Motion hub"
            desc="Turn complex IDX data into clear direction with trending topics and timely insights you can act on."
            cta="Get insights"
            variant="light-on-dark"
          />

          {/* Small card D — blue network */}
          <Card
            href="/research"
            tone="blue"
            heightClass="min-h-[260px]"
            visual={<VisualNetwork />}
            title="Seamlessly query Indonesian markets with conversational AI"
            kicker="Introducing Pyhron Insights™"
            cta="Get started"
            variant="light-on-dark"
          />
        </div>
      </div>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Card primitive
// ───────────────────────────────────────────────────────────────────────────

type Tone = 'indigo' | 'white' | 'teal' | 'black' | 'blue';
type Variant = 'light-on-dark' | 'dark-on-light';

interface CardProps {
  href: string;
  className?: string;
  heightClass?: string;
  tone: Tone;
  visual: React.ReactNode;
  title: string;
  desc?: string;
  kicker?: string;
  cta: string;
  variant: Variant;
}

const toneBg: Record<Tone, string> = {
  indigo: 'bg-gradient-to-br from-[#1e3a8a] via-[#1d4ed8] to-[#312e81]',
  white: 'bg-[#f5f5f7]',
  teal: 'bg-gradient-to-br from-[#99f6e4] via-[#5eead4] to-[#2dd4bf]',
  black: 'bg-[#0a0e1a]',
  blue: 'bg-gradient-to-br from-[#1d4ed8] via-[#1e40af] to-[#0a1628]',
};

function Card({
  href,
  className = '',
  heightClass = 'min-h-[260px]',
  tone,
  visual,
  title,
  desc,
  kicker,
  cta,
  variant,
}: CardProps) {
  const isLight = variant === 'light-on-dark';
  const titleColor = isLight ? 'text-white' : 'text-[#0a0e1a]';
  const descColor = isLight ? 'text-white/75' : 'text-black/60';
  const kickerColor = isLight ? 'text-white/75' : 'text-black/60';
  const ctaBorder = isLight ? 'border-white/60 text-white hover:border-white' : 'border-black/60 text-black hover:border-black';

  return (
    <Link
      href={href}
      className={`group relative overflow-hidden rounded-2xl ${toneBg[tone]} ${heightClass} ${className} transition-transform duration-300 ease-out hover:-translate-y-1`}
    >
      {/* Decorative visual — absolute, behind text */}
      <div className="pointer-events-none absolute inset-0 opacity-90" aria-hidden="true">
        {visual}
      </div>

      {/* Content */}
      <div className="relative flex h-full flex-col justify-between p-7 lg:p-8">
        <div className="max-w-[88%]">
          <h3 className={`text-[22px] font-semibold leading-[1.2] tracking-tight ${titleColor} lg:text-[26px]`}>
            {title}
          </h3>
          {desc && (
            <p className={`mt-3 text-[14px] leading-relaxed ${descColor} lg:text-[15px]`}>
              {desc}
            </p>
          )}
          {kicker && !desc && (
            <p className={`mt-3 text-[14px] leading-relaxed ${kickerColor} lg:text-[15px]`}>
              {kicker}
            </p>
          )}
        </div>
        <span
          className={`mt-6 inline-flex h-10 w-fit items-center gap-2 rounded-full border px-5 text-[13px] font-medium transition-colors ${ctaBorder}`}
        >
          {cta}
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Abstract SVG visuals — lightweight stand-ins for real imagery
// ───────────────────────────────────────────────────────────────────────────

function VisualOrbits() {
  return (
    <svg className="absolute right-[-10%] top-[-10%] h-[130%] w-[90%]" viewBox="0 0 400 500" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="orbit-glow" cx="50%" cy="50%" r="60%">
          <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#1e3a8a" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="260" cy="240" r="180" fill="url(#orbit-glow)" />
      {[0, 20, 40, 60, 80, 100, 120, 140, 160].map((r) => (
        <ellipse
          key={r}
          cx="260"
          cy="240"
          rx={r + 60}
          ry={r * 0.65 + 30}
          fill="none"
          stroke="#93c5fd"
          strokeOpacity={0.35 - r / 400}
          strokeWidth="1"
        />
      ))}
    </svg>
  );
}

function VisualBars() {
  return (
    <svg className="absolute right-0 top-0 h-full w-[55%]" viewBox="0 0 260 300" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bars-fade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.15" />
        </linearGradient>
      </defs>
      {Array.from({ length: 12 }).map((_, i) => {
        const h = 60 + Math.sin(i * 0.9) * 50 + i * 5;
        return (
          <rect
            key={i}
            x={10 + i * 20}
            y={300 - h}
            width={10}
            height={h}
            fill="url(#bars-fade)"
            rx={1}
          />
        );
      })}
    </svg>
  );
}

function VisualWaves() {
  return (
    <svg className="absolute right-0 top-0 h-full w-[60%]" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">
      {[0, 1, 2, 3, 4, 5, 6].map((i) => (
        <path
          key={i}
          d={`M0,${80 + i * 22} C75,${40 + i * 22} 150,${120 + i * 22} 225,${60 + i * 22} S300,${100 + i * 22} 300,${100 + i * 22}`}
          fill="none"
          stroke="#0f766e"
          strokeOpacity={0.35 - i * 0.02}
          strokeWidth="2"
        />
      ))}
    </svg>
  );
}

function VisualLines() {
  return (
    <div className="absolute inset-0 opacity-70">
      <div className="absolute inset-y-0 right-0 w-[50%] bg-gradient-to-l from-white/15 via-white/5 to-transparent" />
      <svg className="absolute right-0 top-0 h-full w-[55%]" viewBox="0 0 300 400" xmlns="http://www.w3.org/2000/svg">
        {Array.from({ length: 28 }).map((_, i) => (
          <line
            key={i}
            x1={i * 12}
            y1={0}
            x2={i * 12 + 80}
            y2={400}
            stroke="#e5e7eb"
            strokeOpacity={0.12 + (i % 3) * 0.08}
            strokeWidth="1"
          />
        ))}
      </svg>
    </div>
  );
}

function VisualNetwork() {
  const nodes = [
    { x: 220, y: 80 }, { x: 260, y: 140 }, { x: 200, y: 180 }, { x: 280, y: 220 },
    { x: 160, y: 240 }, { x: 240, y: 280 }, { x: 300, y: 100 }, { x: 180, y: 120 },
  ];
  return (
    <svg className="absolute right-[-5%] top-[-5%] h-[115%] w-[75%]" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="net-glow" cx="60%" cy="50%" r="55%">
          <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#1e40af" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="240" cy="180" r="160" fill="url(#net-glow)" />
      {nodes.flatMap((a, i) =>
        nodes.slice(i + 1).map((b, j) => (
          <line
            key={`${i}-${j}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="#93c5fd"
            strokeOpacity="0.35"
            strokeWidth="1"
          />
        )),
      )}
      {nodes.map((n, i) => (
        <circle key={i} cx={n.x} cy={n.y} r="3.5" fill="#dbeafe" />
      ))}
    </svg>
  );
}
