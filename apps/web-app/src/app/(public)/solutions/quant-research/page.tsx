import Link from 'next/link';
import { Search, FlaskConical, LineChart } from 'lucide-react';

export const metadata = { title: 'Quantitative Research' };

const steps = [
  {
    icon: Search,
    step: '01',
    title: 'Screen & Discover',
    description: 'Filter 800+ IDX instruments by fundamental, technical, and ML-derived factors to surface research candidates.',
  },
  {
    icon: FlaskConical,
    step: '02',
    title: 'Backtest & Validate',
    description: 'Run walk-forward backtests with IDX-realistic costs and constraints. Evaluate Sharpe, drawdown, and factor exposures.',
  },
  {
    icon: LineChart,
    step: '03',
    title: 'Monitor & Iterate',
    description: 'Track live signal performance against paper portfolios. Refine models with new data and retrain on a rolling basis.',
  },
];

export default function QuantResearchPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-light text-[var(--text-primary)]">
            Data-driven investment research for Indonesian markets
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Combine factor models, ML signals, and fundamental analysis in a single workflow. Purpose-built for IDX market structure and constraints.
          </p>
        </div>
      </section>

      {/* Workflow */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-center text-2xl font-bold text-[var(--text-primary)]">Research Workflow</h2>
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
            Start Research →
          </Link>
        </div>
      </section>
    </div>
  );
}
