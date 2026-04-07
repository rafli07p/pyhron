import Link from 'next/link';
import { BarChart3, TrendingUp, Layers, Activity } from 'lucide-react';

export const metadata = { title: 'Pyhron Indexes' };

const indexes = [
  {
    icon: BarChart3,
    name: 'IHSG',
    fullName: 'Jakarta Composite Index',
    value: '7,284.53',
    change: '+0.42%',
  },
  {
    icon: TrendingUp,
    name: 'LQ45',
    fullName: 'Liquid 45 Index',
    value: '982.17',
    change: '+0.31%',
  },
  {
    icon: Layers,
    name: 'IDX30',
    fullName: 'IDX 30 Index',
    value: '514.60',
    change: '-0.18%',
  },
  {
    icon: Activity,
    name: 'IDX Sector',
    fullName: 'Sector Composite',
    value: '1,127.94',
    change: '+0.56%',
  },
];

export default function IndexesPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-normal text-[var(--text-primary)]">
            IDX Market Indexes and Benchmarks
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Track the Jakarta Composite (IHSG), LQ45, IDX30, and sector indexes in real time. Use Pyhron benchmarks for performance attribution and portfolio analysis across Indonesian capital markets.
          </p>
        </div>
      </section>

      {/* Index Cards */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid gap-6 md:grid-cols-4">
            {indexes.map((idx) => (
              <div key={idx.name} className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-8">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--surface-3)]">
                  <idx.icon className="h-5 w-5 text-[var(--text-primary)]" />
                </span>
                <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">{idx.name}</h3>
                <p className="mt-1 text-xs text-[var(--text-tertiary)]">{idx.fullName}</p>
                <p className="mt-3 font-mono text-lg font-semibold text-[var(--text-primary)]">{idx.value}</p>
                <p className={`mt-1 font-mono text-xs ${idx.change.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>
                  {idx.change}
                </p>
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
            Explore Indexes →
          </Link>
        </div>
      </section>
    </div>
  );
}
