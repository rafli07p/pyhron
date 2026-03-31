import type { Metadata } from 'next';
import { ScreenerView } from '@/components/data/ScreenerView';

export const metadata: Metadata = {
  title: 'Stock Screener',
  description: 'Screen IDX stocks by sector, fundamentals, momentum, and technical indicators.',
};

export default function ScreenerPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">Stock Screener</h1>
      <p className="mt-4 text-text-secondary">
        Filter IDX stocks by sector, market cap, P/E, P/B, ROE, dividend yield, and more.
      </p>
      <div className="mt-12">
        <ScreenerView />
      </div>
    </div>
  );
}
