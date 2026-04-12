'use client';

import Link from 'next/link';
import { HeroSection } from '@/components/hero/HeroSection';
import { ScrollReveal } from '@/components/motion/ScrollReveal';
import { FeaturedSolutions } from '@/components/landing/FeaturedSolutions';
import { IndexTicker } from '@/components/landing/IndexTicker';
import { ResearchInsights } from '@/components/landing/ResearchInsights';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

export default function LandingPage() {
  return (
    <>
      {/* Hero — full viewport, pulled up behind fixed header */}
      <div className="-mt-[88px]">
        <HeroSection />
      </div>

      {/* Live moving ticker of Indonesia's top stock indices */}
      <IndexTicker />

      {/* Featured solutions — MSCI-style card grid */}
      <FeaturedSolutions />

      {/* Research & Insights — MSCI-style editorial grid */}
      <ResearchInsights />

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
