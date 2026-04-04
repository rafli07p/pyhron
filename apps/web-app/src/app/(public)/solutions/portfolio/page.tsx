import Link from 'next/link';
import { PieChart, TrendingUp, Layers } from 'lucide-react';

export const metadata = { title: 'Portfolio Analytics' };

const steps = [
  {
    icon: PieChart,
    step: '01',
    title: 'Connect Portfolio',
    description: 'Import holdings manually or sync from your broker. Track positions, cash, and pending orders in a unified view.',
  },
  {
    icon: TrendingUp,
    step: '02',
    title: 'Measure Performance',
    description: 'Time-weighted and money-weighted returns, benchmark-relative attribution against IHSG, LQ45, or custom indexes.',
  },
  {
    icon: Layers,
    step: '03',
    title: 'Decompose & Optimize',
    description: 'Brinson attribution by sector and factor. Identify drag sources and simulate rebalancing scenarios before execution.',
  },
];

export default function PortfolioPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-light text-[var(--text-primary)]">
            Real-time portfolio monitoring and performance attribution
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Track returns, decompose performance by factor and sector, and benchmark against IDX indexes with institutional-grade analytics.
          </p>
        </div>
      </section>

      {/* Workflow */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-center text-2xl font-bold text-[var(--text-primary)]">Analytics Workflow</h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {steps.map((s) => (
              <div key={s.step} className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-8">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--surface-3)]">
                  <s.icon className="h-5 w-5 text-[var(--text-primary)]" />
                </span>
                <p className="mt-4 font-mono text-xs text-[var(--text-tertiary)]">Step {s.step}</p>
                <h3 className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-0)] py-20">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <Link
            href="/dashboard"
            className="inline-flex h-10 items-center rounded-md bg-[var(--accent-500)] px-6 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
          >
            Open Portfolio →
          </Link>
        </div>
      </section>
    </div>
  );
}
