'use client';

import Link from 'next/link';
import { HeroSection } from '@/components/hero/HeroSection';
import { ScrollReveal } from '@/components/motion/ScrollReveal';
import { CountUp } from '@/components/motion/CountUp';
import { LiveCounter } from '@/components/motion/LiveCounter';
import { FeaturedSolutions } from '@/components/landing/FeaturedSolutions';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

// Fixed (one-shot on scroll) metrics. Data Points is handled separately as a
// continuously-incrementing LiveCounter.
const staticStats = [
  { end: 800, prefix: '', suffix: '+', decimals: 0, label: 'IDX Instruments' },
  { end: 99.97, prefix: '', suffix: '%', decimals: 2, label: 'Uptime SLA' },
  { end: 50, prefix: '<', suffix: 'ms', decimals: 0, label: 'API p99' },
];

const articles = [
  { title: 'Fama-French Five-Factor Model Applied to IDX LQ45', tag: 'Factor Research', href: '/research/articles/fama-french-idx' },
  { title: 'Pairs Trading in Indonesian Banking Sector', tag: 'Strategy', href: '/research/articles/banking-pairs' },
  { title: 'CPO Price Transmission and JPFA/MAIN Correlation', tag: 'Commodity', href: '/research/articles/cpo-correlation' },
];

export default function LandingPage() {
  return (
    <>
      {/* Hero — full viewport, pulled up behind fixed header */}
      <div className="-mt-[88px]">
        <HeroSection />
      </div>

      {/* Trust Metrics — Data Points ticks continuously, others count once on scroll */}
      <section className="border-t border-black/[0.06] bg-white py-20">
        <ScrollReveal preset="fadeUp" stagger={0.15} className="mx-auto grid max-w-6xl grid-cols-2 gap-x-8 gap-y-12 px-6 lg:grid-cols-4">
          {/* Data Points — live-ticking counter */}
          <div className="text-center lg:text-left">
            <LiveCounter
              // Start around "IDR 15.2T" expressed as raw rupiah and tick
              // upward by ~25 million per second so the last few digits
              // visibly move without running off the metric in seconds.
              start={15_203_486_521_000}
              ratePerSecond={25_000_000}
              prefix="IDR "
              className="text-[44px] font-medium tracking-tight text-[#0a0e1a] lg:text-[52px]"
              ariaLabel="Data points, live"
            />
            <p className="mt-3 flex items-center justify-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-black/50 lg:justify-start">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#22c55e] opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#22c55e]" />
              </span>
              Data Points · Live
            </p>
          </div>

          {staticStats.map((s) => (
            <div key={s.label} className="text-center lg:text-left">
              <CountUp
                end={s.end}
                prefix={s.prefix}
                suffix={s.suffix}
                decimals={s.decimals}
                className="text-[44px] font-medium tracking-tight text-[#0a0e1a] lg:text-[52px]"
              />
              <p className="mt-3 text-[11px] font-medium uppercase tracking-[0.12em] text-black/50">{s.label}</p>
            </div>
          ))}
        </ScrollReveal>
      </section>

      {/* Featured solutions — MSCI-style card grid */}
      <FeaturedSolutions />

      {/* Research Previews */}
      <section className="border-t border-black/[0.06] bg-[#f9f9f9] py-24">
        <div className="mx-auto max-w-6xl px-6">
          <ScrollReveal>
            <h2 className="text-2xl font-normal tracking-tight text-black">
              Latest Research
            </h2>
          </ScrollReveal>
          <ScrollReveal preset="fadeUp" stagger={0.15} className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
            {articles.map((article) => (
              <Link
                key={article.title}
                href={article.href}
                className="group rounded-lg border border-black/[0.06] bg-white p-5 transition-all hover:border-[#2563eb]/30 hover:shadow-md"
              >
                <span className="text-[10px] font-medium uppercase tracking-wider text-[#2563eb]">
                  {article.tag}
                </span>
                <h3 className="mt-2 text-sm font-medium leading-snug text-black group-hover:text-[#2563eb]">
                  {article.title}
                </h3>
                <span className="mt-3 block text-xs text-black/40">Read More &rarr;</span>
              </Link>
            ))}
          </ScrollReveal>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-white py-20 text-center">
        <ScrollReveal>
          <h2 className="text-2xl font-normal text-black">
            Ready to elevate your research?
          </h2>
          <div className="mt-6 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-full bg-[#2563eb] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8]"
            >
              Create Free Account &rarr;
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 rounded-full border border-black/15 px-6 py-3 text-sm font-medium text-black/60 transition-colors hover:text-black"
            >
              Schedule Demo &rarr;
            </Link>
          </div>
        </ScrollReveal>
      </section>

      <FinancialDisclaimer className="border-t border-black/[0.06] bg-[#f5f5f5] px-6 py-6" />
    </>
  );
}
