import { Card } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { Check } from 'lucide-react';
import Link from 'next/link';

export const metadata = { title: 'Pricing' };

const plans = [
  {
    name: 'Free',
    price: 'IDR 0',
    period: '/month',
    description: 'Get started with basic research',
    features: ['Market data (delayed 15min)', '5 watchlists', '3 backtests/month', 'Paper trading', 'Community support'],
    cta: 'Get Started',
    highlighted: false,
  },
  {
    name: 'Pro',
    price: 'IDR 499.000',
    period: '/month',
    description: 'For serious quantitative researchers',
    features: ['Real-time market data', 'Unlimited watchlists', 'Unlimited backtests', 'ML signal access', 'Factor analysis', 'Algo execution (paper)', 'Priority support', '3 concurrent sessions'],
    cta: 'Start Pro Trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For institutions and funds',
    features: ['Everything in Pro', 'Live trading (Alpaca)', 'Custom data pipelines', 'Dedicated infrastructure', 'Team management', 'API access', 'SLA guarantee', 'Unlimited sessions'],
    cta: 'Contact Sales',
    highlighted: false,
  },
];

export default function PricingPage() {
  return (
    <div className="py-20">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Simple, transparent pricing</h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">Start free. Scale as you grow.</p>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.name} className={`p-6 ${plan.highlighted ? 'border-[var(--accent-500)] ring-1 ring-[var(--accent-500)]' : ''}`}>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">{plan.name}</h3>
                {plan.highlighted && <Badge variant="accent">Popular</Badge>}
              </div>
              <p className="mt-1 text-sm text-[var(--text-tertiary)]">{plan.description}</p>
              <p className="mt-4">
                <span className="text-3xl font-bold text-[var(--text-primary)]">{plan.price}</span>
                <span className="text-sm text-[var(--text-tertiary)]">{plan.period}</span>
              </p>
              <Button className="mt-6 w-full" variant={plan.highlighted ? 'primary' : 'outline'} asChild>
                <Link href="/register">{plan.cta}</Link>
              </Button>
              <ul className="mt-6 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                    <Check className="h-4 w-4 text-[var(--positive)]" />
                    {f}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
