import { Card } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { Check, Minus } from 'lucide-react';
import Link from 'next/link';

export const metadata = { title: 'Pricing' };

const tiers = [
  {
    name: 'Explorer',
    tagline: 'Watch & Learn',
    price: 'Free',
    period: 'forever',
    description: 'Market observation and discovery',
    cta: 'Get Started',
    ctaHref: '/register',
    highlighted: false,
    features: [
      'Market data (15min delayed)',
      'Basic screener (5 filters)',
      '1 watchlist, 10 instruments',
      'Research previews',
      '3 saved Workbench charts',
      '1 preset dashboard',
      'Metric catalog (browse)',
    ],
    excluded: [
      'No real-time data',
      'No backtesting',
      'No ML signals',
      'No paper/live trading',
      'No custom dashboards',
      'No alerts',
    ],
  },
  {
    name: 'Strategist',
    tagline: 'Build & Test',
    price: 'IDR 499.000',
    period: '/month',
    description: 'Full analytics suite with paper trading',
    cta: 'Start 14-Day Trial',
    ctaHref: '/register?plan=strategist',
    highlighted: true,
    features: [
      'Everything in Explorer, plus:',
      'Real-time market data',
      'Full screener (unlimited filters)',
      'Unlimited watchlists',
      'Full research articles',
      'ML signals + alert config',
      'Workbench (unlimited charts)',
      'Custom dashboards',
      'Backtesting engine',
      'Factor analysis',
      'Risk analytics (VaR, drawdown)',
      'Alerts (up to 50 active)',
      'Data API (1,000 req/day)',
      'CSV data export',
      'Paper trading (full algo execution)',
    ],
    excluded: [
      'No live trading',
      'No team seats',
    ],
  },
  {
    name: 'Operator',
    tagline: 'Deploy & Execute',
    price: 'Custom',
    period: '',
    description: 'Live algorithmic trading with guardrails',
    cta: 'Contact Us',
    ctaHref: '/contact',
    highlighted: false,
    features: [
      'Everything in Strategist, plus:',
      'Live algo execution',
      'VWAP, TWAP, POV, IS algos',
      'Kill switch (manual + auto)',
      'Server-enforced risk guardrails',
      'Unlimited API access',
      'Unlimited alerts',
      'Team seats (up to 10)',
      'Custom ML model deployment',
      'Parquet data export',
      'Priority support (4h SLA)',
      'Dedicated onboarding',
      'Quarterly strategy review',
    ],
    excluded: [],
  },
];

const comparisonFeatures = [
  { name: 'Market data', explorer: 'Delayed', strategist: 'Real-time', operator: 'Real-time' },
  { name: 'Stock screener', explorer: 'Basic', strategist: 'Full', operator: 'Full' },
  { name: 'Watchlists', explorer: '1', strategist: 'Unlimited', operator: 'Unlimited' },
  { name: 'Research articles', explorer: 'Preview', strategist: 'Full', operator: 'Full' },
  { name: 'Workbench charts', explorer: '3 (read)', strategist: 'Unlimited', operator: 'Unlimited' },
  { name: 'Custom dashboards', explorer: '\u2014', strategist: 'Unlimited', operator: 'Unlimited' },
  { name: 'Backtesting', explorer: '\u2014', strategist: '\u2713', operator: '\u2713' },
  { name: 'ML signals', explorer: '\u2014', strategist: '\u2713', operator: '\u2713' },
  { name: 'Factor analysis', explorer: '\u2014', strategist: '\u2713', operator: '\u2713' },
  { name: 'Risk analytics', explorer: '\u2014', strategist: '\u2713', operator: '\u2713' },
  { name: 'Alerts', explorer: '\u2014', strategist: '50', operator: 'Unlimited' },
  { name: 'Paper trading', explorer: '\u2014', strategist: '\u2713', operator: '\u2713' },
  { name: 'Live trading', explorer: '\u2014', strategist: '\u2014', operator: '\u2713' },
  { name: 'Algo execution', explorer: '\u2014', strategist: '\u2014', operator: 'VWAP/TWAP/POV/IS' },
  { name: 'Kill switch', explorer: '\u2014', strategist: '\u2014', operator: '\u2713' },
  { name: 'Data API', explorer: '\u2014', strategist: '1K req/day', operator: 'Unlimited' },
  { name: 'Data export', explorer: '\u2014', strategist: 'CSV', operator: 'CSV + Parquet' },
  { name: 'Team seats', explorer: '\u2014', strategist: '\u2014', operator: 'Up to 10' },
  { name: 'Support', explorer: 'Community', strategist: 'Email', operator: 'Priority (SLA)' },
];

export default function PricingPage() {
  return (
    <div className="py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-text-primary text-3xl font-bold">Choose Your Edge</h1>
          <p className="text-text-secondary mt-2 text-sm">
            From market observation to live execution.
          </p>
        </div>

        {/* Tier Cards */}
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {tiers.map((tier) => (
            <Card
              key={tier.name}
              className={`flex flex-col p-6 ${tier.highlighted ? 'border-[var(--accent-500)] ring-1 ring-[var(--accent-500)]' : ''}`}
            >
              {tier.highlighted && (
                <div className="mb-4">
                  <Badge variant="accent">Popular</Badge>
                </div>
              )}
              <h3 className="text-text-primary text-lg font-semibold">{tier.name}</h3>
              <p className="text-text-tertiary text-xs font-medium uppercase tracking-wider">
                {tier.tagline}
              </p>
              <p className="text-text-tertiary mt-1 text-sm">{tier.description}</p>
              <p className="mt-4">
                <span className="text-text-primary text-3xl font-bold">{tier.price}</span>
                {tier.period && (
                  <span className="text-text-tertiary text-sm"> {tier.period}</span>
                )}
              </p>
              <Button
                className="mt-6 w-full"
                variant={tier.highlighted ? 'primary' : 'outline'}
                asChild
              >
                <Link href={tier.ctaHref}>{tier.cta}</Link>
              </Button>
              <ul className="mt-6 space-y-2">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className="text-text-secondary flex items-start gap-2 text-sm"
                  >
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--positive)]" />
                    {f}
                  </li>
                ))}
                {tier.excluded.map((f) => (
                  <li
                    key={f}
                    className="text-text-tertiary flex items-start gap-2 text-sm"
                  >
                    <Minus className="mt-0.5 h-4 w-4 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>

        {/* Feature Comparison */}
        <div className="mt-20">
          <h2 className="text-text-primary text-center text-2xl font-bold">
            Feature Comparison
          </h2>
          <div className="mt-8 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-text-secondary py-3 text-left font-medium">Feature</th>
                  <th className="text-text-secondary py-3 text-center font-medium">Explorer</th>
                  <th className="text-text-secondary py-3 text-center font-medium">Strategist</th>
                  <th className="text-text-secondary py-3 text-center font-medium">Operator</th>
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map((row) => (
                  <tr
                    key={row.name}
                    className="border-b border-[var(--border-default)]"
                  >
                    <td className="text-text-primary py-3">{row.name}</td>
                    <td className="text-text-secondary py-3 text-center">{row.explorer}</td>
                    <td className="text-text-secondary py-3 text-center">{row.strategist}</td>
                    <td className="text-text-secondary py-3 text-center">{row.operator}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-20">
          <h2 className="text-text-primary text-center text-2xl font-bold">
            Frequently Asked Questions
          </h2>
          <div className="mx-auto mt-8 max-w-3xl space-y-4">
            {[
              {
                q: 'Can I upgrade or downgrade anytime?',
                a: 'Yes. Upgrades take effect immediately. Downgrades take effect at the end of your billing cycle. Your data is never deleted.',
              },
              {
                q: 'How does paper trading work?',
                a: 'Paper trading uses real market data with simulated execution. It applies IDX lot sizes, tick sizes, and commission/tax rules. No real capital is at risk.',
              },
              {
                q: 'What are the requirements for Operator access?',
                a: 'Operator requires minimum 30 days of paper trading history, 50+ paper trades, a KYC review, and an onboarding call to configure risk guardrails.',
              },
              {
                q: 'Do you offer annual pricing?',
                a: 'Yes. Annual plans receive a 20% discount. Contact us for enterprise and institutional pricing.',
              },
              {
                q: 'Is there a student discount?',
                a: 'We offer 50% off Strategist for verified students and academic researchers. Contact us with your .ac.id email.',
              },
            ].map((faq) => (
              <Card key={faq.q} className="p-4">
                <h3 className="text-text-primary text-sm font-semibold">{faq.q}</h3>
                <p className="text-text-secondary mt-1 text-sm">{faq.a}</p>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
