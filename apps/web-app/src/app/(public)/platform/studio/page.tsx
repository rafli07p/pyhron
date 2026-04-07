import Link from 'next/link';
import { PenTool, LayoutDashboard, Filter } from 'lucide-react';

export const metadata = { title: 'Pyhron Studio' };

const features = [
  {
    icon: PenTool,
    title: 'Workbench',
    description: 'No-code chart builder with 15+ technical indicators. Overlay moving averages, Bollinger Bands, RSI, and custom factor scores on any IDX instrument.',
  },
  {
    icon: LayoutDashboard,
    title: 'Dashboards',
    description: 'Customizable analytics with drag-and-drop tiles. Combine charts, tables, heatmaps, and alerts into a single view tailored to your workflow.',
  },
  {
    icon: Filter,
    title: 'Screener',
    description: 'Multi-factor filtering across 800+ IDX instruments. Screen by fundamental, technical, and ML-derived signals with real-time updates.',
  },
];

export default function StudioPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-normal text-[var(--text-primary)]">
            Your analytical workspace for IDX research
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Build custom charts with 15+ technical indicators, create dashboards with drag-and-drop tiles, and run multi-factor stock screening across 800+ IDX instruments.
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
            href="/dashboard"
            className="inline-flex h-10 items-center rounded-md bg-[var(--accent-500)] px-6 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
          >
            Launch Terminal →
          </Link>
        </div>
      </section>
    </div>
  );
}
