import type { Metadata } from 'next';
import { IndexDashboard } from '@/components/data/IndexDashboard';

export const metadata: Metadata = {
  title: 'Index Dashboard',
  description: 'Pyhron factor index performance dashboard with historical data and analytics.',
};

export default function IndicesPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">Index Dashboard</h1>
      <p className="mt-4 text-text-secondary">
        Factor index performance, constituents, and analytics for IDX equities.
      </p>
      <div className="mt-12">
        <IndexDashboard />
      </div>
    </div>
  );
}
