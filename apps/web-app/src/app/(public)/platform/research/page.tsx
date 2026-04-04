import Link from 'next/link';
import { BrainCircuit, BarChart3, FlaskConical } from 'lucide-react';

export const metadata = { title: 'Pyhron Research' };

const features = [
  {
    icon: BrainCircuit,
    title: 'ML Signals',
    description: 'Ensemble models trained on IDX-specific data generate daily buy, hold, and sell signals with confidence scores for every covered instrument.',
  },
  {
    icon: BarChart3,
    title: 'Factor Analysis',
    description: 'Decompose returns across momentum, value, quality, and volatility factors. Identify which exposures drive your portfolio performance.',
  },
  {
    icon: FlaskConical,
    title: 'Backtesting',
    description: 'Walk-forward backtesting engine with realistic IDX transaction costs, lot sizes, and auto-rejection price limits built in.',
  },
];

export default function ResearchPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-light text-[var(--text-primary)]">
            ML-driven signals and factor analysis
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Leverage machine learning models trained on IDX-specific data. Generate momentum, value, quality, and volatility signals with confidence scoring.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div key={f.title} className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-8">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--surface-3)]">
                  <f.icon className="h-5 w-5 text-[var(--text-primary)]" />
                </span>
                <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-0)] py-20">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <Link
            href="/research"
            className="inline-flex h-10 items-center rounded-md bg-[var(--accent-500)] px-6 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
          >
            View Research →
          </Link>
        </div>
      </section>
    </div>
  );
}
