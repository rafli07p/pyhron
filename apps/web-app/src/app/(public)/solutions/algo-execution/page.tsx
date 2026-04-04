import Link from 'next/link';
import { Route, Cpu, ShieldCheck } from 'lucide-react';

export const metadata = { title: 'Algorithmic Execution' };

const steps = [
  {
    icon: Cpu,
    step: '01',
    title: 'Configure Algorithm',
    description: 'Select from VWAP, TWAP, POV, and Implementation Shortfall algorithms tuned for IDX liquidity profiles.',
  },
  {
    icon: Route,
    step: '02',
    title: 'Route & Execute',
    description: 'Smart order routing slices orders across sessions, respects lot sizes and tick rules, and adapts to real-time volume.',
  },
  {
    icon: ShieldCheck,
    step: '03',
    title: 'Monitor & Safeguard',
    description: 'Real-time execution dashboard with kill switch, slippage tracking, and server-enforced risk guardrails.',
  },
];

export default function AlgoExecutionPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-light text-[var(--text-primary)]">
            Smart order routing with IDX-native algorithms
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Execute strategies with algorithms purpose-built for IDX market microstructure. Minimize market impact with adaptive slicing and session-aware scheduling.
          </p>
        </div>
      </section>

      {/* Workflow */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-center text-2xl font-bold text-[var(--text-primary)]">Execution Workflow</h2>
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
            Try Algo Execution →
          </Link>
        </div>
      </section>
    </div>
  );
}
