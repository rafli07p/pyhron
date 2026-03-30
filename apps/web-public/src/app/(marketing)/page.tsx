import type { Metadata } from 'next';
import { Hero } from '@/components/marketing/Hero';
import { IndexTicker } from '@/components/shared/IndexTicker';
import { InsightsSection } from '@/components/marketing/InsightsSection';
import { IndexPreview } from '@/components/marketing/IndexPreview';
import { SolutionsSection } from '@/components/marketing/SolutionsSection';
import { TrustBar } from '@/components/marketing/TrustBar';
import { CTABanner } from '@/components/marketing/CTABanner';

export const metadata: Metadata = {
  title: 'Pyhron - Quantitative Analytics and Trading for IDX',
  description:
    'Factor models, algorithmic trading, and portfolio analytics for the Indonesia Stock Exchange.',
  openGraph: {
    title: 'Pyhron',
    description: 'Quantitative analytics and trading for IDX',
    url: 'https://pyhron.com',
    siteName: 'Pyhron',
    images: [{ url: '/images/og/homepage.jpg', width: 1200, height: 630 }],
    locale: 'en_US',
    type: 'website',
  },
  twitter: { card: 'summary_large_image' },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <IndexTicker />
      <InsightsSection />
      <IndexPreview />
      <SolutionsSection />
      <TrustBar />
      <CTABanner />
    </>
  );
}
