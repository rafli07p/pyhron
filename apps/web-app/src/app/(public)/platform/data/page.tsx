import Link from 'next/link';
import { Radio, Database, Code } from 'lucide-react';

export const metadata = { title: 'Pyhron Data' };

const features = [
  {
    icon: Radio,
    title: 'Real-time Feeds',
    description: 'Stream live price, volume, and order book data for 800+ IDX instruments with sub-second latency via WebSocket connections.',
  },
  {
    icon: Database,
    title: 'Historical Data',
    description: 'Access up to 10 years of daily OHLCV data, corporate actions, and fundamental snapshots for backtesting and factor research.',
  },
  {
    icon: Code,
    title: 'Data API',
    description: 'Unified REST and WebSocket API abstracting yfinance, EODHD, and Alpaca data feeds. One schema, multiple providers, automatic failover.',
  },
];

export default function DataPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="text-3xl font-normal text-[var(--text-primary)]">
            Market data infrastructure for Indonesian capital markets
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
            Access real-time and historical data for 800+ IDX instruments. Connect to yfinance, EODHD, and Alpaca data feeds through a unified API.
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
            Explore Data →
          </Link>
        </div>
      </section>
    </div>
  );
}
