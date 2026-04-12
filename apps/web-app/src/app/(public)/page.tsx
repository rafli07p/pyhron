'use client';

import { HeroSection } from '@/components/hero/HeroSection';
import { FeaturedSolutions } from '@/components/landing/FeaturedSolutions';
import { IndexTicker } from '@/components/landing/IndexTicker';
import { ResearchInsights } from '@/components/landing/ResearchInsights';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

export default function LandingPage() {
  return (
    <>
      {/* Hero — full viewport, pulled up behind fixed header */}
      <div className="-mt-[108px]">
        <HeroSection />
      </div>

      {/* Live moving ticker of Indonesia's top stock indices */}
      <IndexTicker />

      {/* Featured solutions — MSCI-style card grid */}
      <FeaturedSolutions />

      {/* Research & Insights — MSCI-style editorial grid */}
      <ResearchInsights />

      <FinancialDisclaimer className="border-t border-black/[0.06] bg-[#f5f5f5] px-6 py-6" />
    </>
  );
}
