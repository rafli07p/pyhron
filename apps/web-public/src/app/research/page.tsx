import type { Metadata } from 'next';
import { ResearchHub } from '@/components/research/ResearchHub';

export const metadata: Metadata = {
  title: 'Research',
  description: 'Quantitative research, market commentary, and factor analysis for IDX equities.',
};

export default function ResearchPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">Research & Insights</h1>
      <p className="mt-4 text-text-secondary">
        Quantitative research, market commentary, and factor analysis for Indonesian equities.
      </p>
      <div className="mt-12">
        <ResearchHub />
      </div>
    </div>
  );
}
