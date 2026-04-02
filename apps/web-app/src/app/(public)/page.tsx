import { Hero } from '@/components/landing/hero';
import { StatsBar } from '@/components/landing/stats-bar';
import { Features } from '@/components/landing/features';
import { ResearchPreview } from '@/components/landing/research-preview';
import { PlatformPreview } from '@/components/landing/platform-preview';
import { CtaBanner } from '@/components/landing/cta-banner';

export default function LandingPage() {
  return (
    <>
      <Hero />
      <StatsBar />
      <Features />
      <ResearchPreview />
      <PlatformPreview />
      <CtaBanner />
    </>
  );
}
