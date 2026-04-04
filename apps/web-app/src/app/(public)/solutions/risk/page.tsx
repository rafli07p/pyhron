import Link from 'next/link';
import { ShieldAlert, BarChart3, Bell } from 'lucide-react';

export const metadata = { title: 'Risk Management' };

const steps = [
  {
    icon: ShieldAlert,
    step: '01',
    title: 'Define Risk Framework',
    description: 'Set VaR limits, maximum drawdown thresholds, and sector concentration caps aligned with your investment mandate.',
  },
  {
    icon: BarChart3,
    step: '02',
    title: 'Monitor Exposures',
    description: 'Real-time risk dashboard showing VaR, CVaR, beta, and factor exposures across your entire IDX portfolio.',
  },
  {
    icon: Bell,
    step: '03',
    title: 'Alert & Act',
    description: 'Automated alerts when risk metrics breach thresholds. Kill switch integration halts execution before limits are exceeded.',
  },
];

export default function RiskPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-light text-[var(--text-primary)]">
            Institutional-grade risk analytics for IDX portfolios
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Monitor portfolio risk in real time with VaR, CVaR, stress testing, and factor decomposition calibrated to IDX market dynamics.
          </p>
        </div>
      </section>

      {/* Workflow */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-center text-2xl font-bold text-[var(--text-primary)]">Risk Workflow</h2>
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
            View Risk Analytics →
          </Link>
        </div>
      </section>
    </div>
  );
}
