import Link from 'next/link';

export const metadata = { title: 'About' };

const stats = [
  { value: '2025', label: 'Platform founded' },
  { value: '800+', label: 'IDX instruments' },
  { value: '144', label: 'Metrics available' },
  { value: '18', label: 'Alpha factors' },
];

const cards = [
  {
    title: 'Company',
    description:
      'Pyhron builds institutional-grade quantitative research infrastructure for Indonesian capital markets. We deliver professional analytics, systematic strategies, and execution tools in a single integrated platform.',
  },
  {
    title: 'Our Vision',
    description:
      'To become the definitive quantitative research platform for Southeast Asian markets, starting with Indonesia. We aim to set the standard for data quality, analytical rigor, and systematic investing in emerging markets.',
  },
  {
    title: 'Our Mission',
    description:
      'Democratize quantitative finance for the Indonesian market by providing tools and infrastructure previously accessible only to large institutional desks. Make evidence-based investing the norm, not the exception.',
  },
];

const timeline = [
  { quarter: '2025 Q1', version: 'v0.1.0', title: 'Foundation', description: 'Core data pipeline, market data ingestion from EODHD and yfinance, initial factor library with 18 alpha factors.' },
  { quarter: '2025 Q2', version: 'v0.1.1', title: 'Analytics Layer', description: 'Risk analytics engine, VaR/CVaR calculations, portfolio attribution, and real-time alert system.' },
  { quarter: '2025 Q3', version: 'v0.2.0', title: 'Execution Engine', description: 'Paper trading simulator, VWAP/TWAP execution algorithms, order management system with IDX-specific rules.' },
  { quarter: '2025 Q4', version: 'v0.2.1', title: 'ML Pipeline', description: 'Ensemble model training infrastructure, walk-forward validation, signal generation with confidence scoring.' },
  { quarter: '2026 Q1', version: 'v0.3.0', title: 'Studio Workbench', description: 'Custom dashboard builder, strategy studio with visual backtesting, collaborative workspaces for research teams.' },
];

const philosophy = [
  {
    icon: '{}',
    title: 'Seams Before Implementation',
    description: 'Every service boundary is defined by Protobuf contracts before a single line of business logic is written. This ensures type safety across Python, TypeScript, and Go services.',
  },
  {
    icon: '\u21BB',
    title: 'Event Sourcing for All State',
    description: 'All state mutations flow through Apache Kafka as immutable events. This gives us full audit trails, replay capability, and natural decoupling between services.',
  },
  {
    icon: '\u26A0',
    title: 'Fail Explicit, Not Silent',
    description: 'Every failed message lands in a dead letter queue with full context. We never swallow errors. If something breaks, the system tells you exactly what, where, and why.',
  },
];

const idxPoints = [
  'Full coverage of 800+ instruments listed on the Indonesia Stock Exchange with T+2 settlement modeling',
  'IDX-specific tick size rules, lot size constraints (100 shares), and auto-rejection price limits built into every calculation',
  'Realistic transaction cost modeling: 0.15% buy commission, 0.25% sell commission including 0.1% final income tax',
  'Trading session awareness (Session I: 09:00-11:30, Session II: 13:30-15:00 WIB) for accurate intraday analytics',
];

export default function AboutPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight tracking-tight text-[var(--text-primary)] md:text-5xl">
            Setting the standard in quantitative research for Indonesian markets
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-[var(--text-secondary)]">
            Empowering institutional investors and systematic traders with professional-grade analytics, data infrastructure, and execution tools purpose-built for the IDX.
          </p>
          <Link
            href="/contact"
            className="mt-8 inline-flex h-10 items-center rounded-md bg-[var(--accent-500)] px-6 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
          >
            Contact Us
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-[var(--border-default)] bg-[var(--surface-1)]">
        <div className="mx-auto grid max-w-7xl grid-cols-2 divide-x divide-[var(--border-default)] md:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="px-6 py-10 text-center">
              <p className="font-mono text-3xl font-semibold text-[var(--text-primary)]">{s.value}</p>
              <p className="mt-1 text-xs text-[var(--text-tertiary)]">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Who We Are */}
      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Who We Are</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {cards.map((c) => (
              <div key={c.title} className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-8">
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">{c.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">{c.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-1)] py-20">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">History</h2>
          <div className="mt-10 space-y-10">
            {timeline.map((t, i) => (
              <div key={t.quarter} className="relative pl-8 before:absolute before:left-0 before:top-1 before:w-px before:bg-[var(--border-default)]" style={{ ['--tw-before-h' as string]: i < timeline.length - 1 ? '100%' : '0' }}>
                <span className="absolute left-[-4px] top-1.5 h-2 w-2 rounded-full bg-[var(--accent-500)]" />
                <div className="flex items-center gap-3">
                  <span className="rounded bg-[var(--accent-100)] px-2 py-0.5 font-mono text-xs text-[var(--accent-500)]">{t.version}</span>
                  <span className="text-xs text-[var(--text-tertiary)]">{t.quarter}</span>
                </div>
                <h3 className="mt-2 text-sm font-semibold text-[var(--text-primary)]">{t.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-[var(--text-secondary)]">{t.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Philosophy */}
      <section className="border-t border-[var(--border-default)] py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Technical Philosophy</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {philosophy.map((p) => (
              <div key={p.title} className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-8">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--surface-3)] font-mono text-lg text-[var(--text-primary)]">{p.icon}</span>
                <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{p.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* IDX Focus */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-1)] py-20">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Purpose-built for Indonesia</h2>
          <p className="mt-3 text-sm text-[var(--text-secondary)]">
            Every component of Pyhron is designed around the specific rules, constraints, and opportunities of the Indonesia Stock Exchange.
          </p>
          <ul className="mt-8 space-y-4">
            {idxPoints.map((point) => (
              <li key={point} className="flex gap-3 text-sm leading-relaxed text-[var(--text-secondary)]">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[var(--accent-500)]" />
                {point}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
