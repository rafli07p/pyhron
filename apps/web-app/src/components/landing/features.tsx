import { BarChart3, Cpu, Zap } from 'lucide-react';
import Link from 'next/link';

const features = [
  {
    icon: BarChart3,
    title: 'Market Intelligence',
    description:
      'Real-time IDX data, multi-factor models, and ML-driven research signals. Full LQ45 and IDX80 coverage with proprietary alpha factors.',
    href: '/methodology',
  },
  {
    icon: Cpu,
    title: 'Strategy Engine',
    description:
      'Backtest, optimize, and deploy quantitative strategies at scale. Walk-forward validation, risk-adjusted metrics, and Monte Carlo analysis.',
    href: '/studio/backtests',
  },
  {
    icon: Zap,
    title: 'Execution Layer',
    description:
      'Smart order routing with VWAP, TWAP, and IS algorithms. Server-enforced risk guardrails, kill switch, and IDX lot-size aware execution.',
    href: '/execution',
  },
];

export function Features() {
  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-6">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#6B7280]">
          What We Do
        </p>
        <h2 className="mt-4 text-3xl font-normal tracking-tight text-[#1A1A2E] lg:text-4xl">
          Infrastructure for systematic investing
        </h2>

        <div className="mt-16 grid grid-cols-1 gap-12 md:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div key={feature.title} className="group">
                <div className="flex h-12 w-12 items-center justify-center border border-[#E5E7EB] transition-colors group-hover:border-[#C9A84C]">
                  <Icon className="h-5 w-5 text-[#0A1628]" strokeWidth={1.5} />
                </div>
                <h3 className="mt-6 text-lg font-medium text-[#1A1A2E]">{feature.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-[#6B7280]">{feature.description}</p>
                <Link
                  href={feature.href}
                  className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[#0A1628] transition-colors hover:text-[#C9A84C]"
                >
                  Learn More
                  <span className="transition-transform group-hover:translate-x-0.5">&rarr;</span>
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
