export const metadata = { title: 'Changelog' };

type Badge = 'Feature' | 'Improvement' | 'Fix';

interface Release {
  version: string;
  date: string;
  title: string;
  badges: Badge[];
  items: string[];
}

const releases: Release[] = [
  {
    version: 'v0.3.0',
    date: 'March 2026',
    title: 'Studio Workbench & Custom Dashboards',
    badges: ['Feature', 'Improvement'],
    items: [
      'Custom dashboard builder with drag-and-drop widget placement and persistent layouts',
      'Strategy studio with visual backtesting interface and parameter sweep tooling',
      'Collaborative workspaces allowing research teams to share strategies and annotations',
      'New charting engine with 30+ technical indicators and multi-timeframe support',
    ],
  },
  {
    version: 'v0.2.0',
    date: 'January 2026',
    title: 'Paper Trading & Execution',
    badges: ['Feature', 'Improvement'],
    items: [
      'Paper trading simulator with realistic IDX order matching and T+2 settlement',
      'VWAP and TWAP execution algorithms with historical volume profile modeling',
      'Order management system with IDX lot size, tick size, and auto-rejection rules',
      'Real-time P&L tracking with transaction cost attribution and slippage analysis',
    ],
  },
  {
    version: 'v0.1.1',
    date: 'December 2025',
    title: 'Risk Analytics & Alerts',
    badges: ['Feature', 'Fix'],
    items: [
      'Portfolio risk engine with VaR, CVaR, and maximum drawdown calculations',
      'Configurable alert system for price, volume, and factor exposure thresholds',
      'Fixed data gap handling in EODHD pipeline for IDX holiday schedules',
    ],
  },
  {
    version: 'v0.1.0',
    date: 'November 2025',
    title: 'Initial Release',
    badges: ['Feature'],
    items: [
      'Core data pipeline ingesting 800+ IDX instruments from EODHD and yfinance',
      'Factor library with 18 alpha factors across momentum, value, quality, and volatility',
      'Web application with market overview, instrument detail, and portfolio views',
    ],
  },
];

const badgeColors: Record<Badge, string> = {
  Feature: 'bg-[var(--accent-100)] text-[var(--accent-500)]',
  Improvement: 'bg-blue-500/10 text-blue-400',
  Fix: 'bg-amber-500/10 text-amber-400',
};

export default function ChangelogPage() {
  return (
    <div className="py-20">
      <div className="mx-auto max-w-3xl px-6">
        <h1 className="text-3xl font-bold text-[var(--text-primary)]">Changelog</h1>
        <p className="mt-3 text-sm text-[var(--text-secondary)]">
          Track platform updates and new features.
        </p>

        <div className="mt-14 space-y-16">
          {releases.map((release) => (
            <article key={release.version}>
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded bg-[var(--accent-100)] px-2.5 py-0.5 font-mono text-sm font-semibold text-[var(--accent-500)]">
                  {release.version}
                </span>
                <span className="text-xs text-[var(--text-tertiary)]">{release.date}</span>
                {release.badges.map((badge) => (
                  <span
                    key={badge}
                    className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${badgeColors[badge]}`}
                  >
                    {badge}
                  </span>
                ))}
              </div>
              <h2 className="mt-3 text-lg font-semibold text-[var(--text-primary)]">
                {release.title}
              </h2>
              <ul className="mt-4 space-y-2.5">
                {release.items.map((item) => (
                  <li key={item} className="flex gap-3 text-sm leading-relaxed text-[var(--text-secondary)]">
                    <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[var(--text-tertiary)]" />
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
