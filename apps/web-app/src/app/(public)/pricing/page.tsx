import Link from 'next/link';

export const metadata = { title: 'Pricing' };

const tiers = [
  {
    name: 'Explorer',
    tagline: 'Watch & Learn',
    price: 'Free',
    period: '',
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

const faqs = [
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
];

export default function PricingPage() {
  return (
    <div className="bg-white py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-black">Choose Your Edge</h1>
          <p className="mt-2 text-sm text-black/50">
            From market observation to live execution.
          </p>
        </div>

        {/* Tier Cards */}
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`flex flex-col rounded-xl bg-white p-8 ${
                tier.highlighted
                  ? 'border-2 border-[#2563eb]'
                  : 'border border-black/[0.08]'
              }`}
            >
              {tier.highlighted && (
                <div className="mb-4">
                  <span className="inline-block rounded-full bg-[#2563eb]/10 px-3 py-1 text-xs font-semibold text-[#2563eb]">
                    Popular
                  </span>
                </div>
              )}
              <h3 className="text-lg font-bold text-black">{tier.name}</h3>
              <p className="text-xs font-medium uppercase tracking-wider text-black/40">
                {tier.tagline}
              </p>
              <p className="mt-1 text-sm text-black/50">{tier.description}</p>
              <p className="mt-4">
                <span className="text-4xl font-bold text-black">{tier.price}</span>
                {tier.period && (
                  <span className="text-sm text-black/40"> {tier.period}</span>
                )}
              </p>
              <Link
                href={tier.ctaHref}
                className={`mt-6 block w-full rounded-full py-3 text-center text-sm font-medium transition-colors ${
                  tier.highlighted
                    ? 'bg-[#2563eb] text-white hover:bg-[#1d4ed8]'
                    : 'border border-black/[0.08] text-black hover:bg-black/[0.03]'
                }`}
              >
                {tier.cta}
              </Link>
              <ul className="mt-6 space-y-2">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2 text-sm text-black/60"
                  >
                    <span className="mt-0.5 shrink-0 text-green-600">&#10003;</span>
                    {f}
                  </li>
                ))}
                {tier.excluded.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2 text-sm text-black/40"
                  >
                    <span className="mt-0.5 shrink-0">&mdash;</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="mx-auto mt-20 max-w-2xl">
          <h2 className="text-center text-2xl font-semibold text-black">FAQ</h2>
          {faqs.map((faq) => (
            <div key={faq.q} className="mt-6 border-b border-black/[0.06] pb-6">
              <h3 className="text-sm font-semibold text-black">{faq.q}</h3>
              <p className="mt-2 text-sm text-black/50">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
