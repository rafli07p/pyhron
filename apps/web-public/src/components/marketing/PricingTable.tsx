import Link from 'next/link';
import { Check, X } from 'lucide-react';

interface PricingFeature {
  label: string;
  free: string | boolean;
  pro: string | boolean;
  enterprise: string | boolean;
}

const features: PricingFeature[] = [
  { label: 'IDX Screener', free: 'Basic (5 filters)', pro: 'Full (all filters)', enterprise: 'Full + custom' },
  { label: 'Historical Data', free: '1 year', pro: '10 years', enterprise: 'Full history' },
  { label: 'Backtesting', free: '1 strategy', pro: 'Unlimited', enterprise: 'Unlimited + custom' },
  { label: 'API Access', free: '100 calls/day', pro: '10.000 calls/day', enterprise: 'Unlimited' },
  { label: 'Live Trading', free: false, pro: 'Paper only', enterprise: 'Paper + Live' },
  { label: 'Research', free: 'Public only', pro: 'Full access', enterprise: 'Full + custom reports' },
  { label: 'Support', free: 'Community', pro: 'Email', enterprise: 'Dedicated' },
];

const tiers = [
  { name: 'Free', price: 'Rp 0', period: '', cta: 'Get Started', href: '/register', highlight: false },
  { name: 'Pro', price: 'Rp 2.500.000', period: '/mo', cta: 'Start Pro Trial', href: '/register', highlight: true },
  { name: 'Enterprise', price: 'Custom', period: '', cta: 'Contact Sales', href: '/contact', highlight: false },
];

function FeatureValue({ value }: { value: string | boolean }) {
  if (value === true) return <Check className="h-4 w-4 text-positive mx-auto" />;
  if (value === false) return <X className="h-4 w-4 text-text-muted mx-auto" />;
  return <span className="text-sm text-text-secondary">{value}</span>;
}

export function PricingTable() {
  return (
    <div className="mx-auto max-w-content">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {tiers.map((tier) => (
          <div
            key={tier.name}
            className={`rounded-lg border p-6 ${
              tier.highlight
                ? 'border-accent-500 bg-bg-secondary shadow-lg'
                : 'border-border bg-bg-primary'
            }`}
          >
            <h3 className="text-lg font-medium text-text-primary">{tier.name}</h3>
            <div className="mt-4">
              <span className="font-display text-3xl text-text-primary">{tier.price}</span>
              {tier.period && <span className="text-text-muted">{tier.period}</span>}
            </div>
            <Link
              href={tier.href}
              className={`mt-6 block w-full rounded-md px-4 py-2 text-center text-sm font-medium transition-colors ${
                tier.highlight
                  ? 'bg-accent-500 text-primary-900 hover:bg-accent-600'
                  : 'border border-border hover:bg-bg-tertiary'
              }`}
            >
              {tier.cta}
            </Link>
            <ul className="mt-6 space-y-3">
              {features.map((feature) => {
                const value = tier.name === 'Free' ? feature.free : tier.name === 'Pro' ? feature.pro : feature.enterprise;
                return (
                  <li key={feature.label} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{feature.label}</span>
                    <FeatureValue value={value} />
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
