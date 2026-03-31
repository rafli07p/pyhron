import type { Metadata } from 'next';
import { PricingTable } from '@/components/marketing/PricingTable';

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Pyhron pricing plans: Free, Pro (Rp 2.500.000/mo), and Enterprise.',
};

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <div className="text-center">
        <h1 className="font-display text-4xl text-text-primary md:text-5xl">Pricing</h1>
        <p className="mt-4 text-text-secondary">
          Choose the plan that fits your trading and research needs.
        </p>
      </div>
      <div className="mt-12">
        <PricingTable />
      </div>
    </div>
  );
}
