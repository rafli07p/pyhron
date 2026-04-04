import Link from 'next/link';

export const metadata = { title: 'Methodology' };

const sections = [
  { id: 'data-sources', label: 'Data Sources' },
  { id: 'factor-construction', label: 'Factor Construction' },
  { id: 'signal-generation', label: 'Signal Generation' },
  { id: 'backtesting', label: 'Backtesting Framework' },
  { id: 'risk-metrics', label: 'Risk Metrics' },
  { id: 'execution', label: 'Execution Algorithms' },
];

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-20">
      <div className="flex gap-16">
        {/* Sidebar */}
        <nav className="hidden w-[200px] flex-shrink-0 md:block">
          <div className="sticky top-24">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
              Contents
            </p>
            <ul className="mt-4 space-y-2.5">
              {sections.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`#${s.id}`}
                    className="text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
                  >
                    {s.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        {/* Content */}
        <div className="min-w-0 max-w-[700px]">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Methodology</h1>
          <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
            A detailed overview of the quantitative framework, data infrastructure, and analytical methods underpinning the Pyhron platform.
          </p>

          <section id="data-sources" className="mt-16">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Data Sources</h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Pyhron ingests market data from multiple providers to ensure completeness and fault tolerance. Our primary source is <strong className="text-[var(--text-primary)] font-medium">EODHD</strong>, which provides end-of-day and fundamental data for all IDX-listed instruments. We use <strong className="text-[var(--text-primary)] font-medium">yfinance</strong> as a secondary source for validation and gap-filling.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              For intraday analysis, we consume <strong className="text-[var(--text-primary)] font-medium">IDX tick data</strong> directly, capturing order book snapshots and trade prints during both trading sessions (Session I: 09:00-11:30, Session II: 13:30-15:00 WIB). All data passes through a validation pipeline that checks for completeness, consistency, and outlier detection before entering the analytical layer.
            </p>
          </section>

          <section id="factor-construction" className="mt-16">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Factor Construction</h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Our factor library contains 18 alpha factors spanning momentum, value, quality, and volatility categories. Factors are computed daily after market close and stored as normalized z-scores across the investable universe.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              As an example, the 12-month momentum factor is computed as:
            </p>
            <div className="mt-3 rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] px-4 py-3">
              <code className="font-mono text-sm text-[var(--text-primary)]">MOM = P(t-1) / P(t-12) - 1</code>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              Where P(t-1) is the price at the end of the previous month and P(t-12) is the price twelve months prior. We skip the most recent month to avoid short-term reversal effects. All factors are winsorized at the 1st and 99th percentiles to mitigate outlier influence.
            </p>
          </section>

          <section id="signal-generation" className="mt-16">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Signal Generation</h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Trading signals are produced by an ML ensemble that combines XGBoost, LightGBM, and LSTM networks. Each model is trained on a rolling window of historical factor exposures and forward returns. The ensemble output is a weighted average where weights are determined by recent out-of-sample performance.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              Every signal includes a confidence score (0-1) and an expected return estimate. Signals below a configurable confidence threshold are discarded. Models are retrained weekly using walk-forward methodology to prevent look-ahead bias.
            </p>
          </section>

          <section id="backtesting" className="mt-16">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Backtesting Framework</h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Our backtesting engine uses <strong className="text-[var(--text-primary)] font-medium">walk-forward validation</strong> to simulate realistic strategy performance. The historical period is divided into sequential train/test windows. The model is trained on each training window and evaluated on the subsequent test window, then the window slides forward.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              <strong className="text-[var(--text-primary)] font-medium">Slippage modeling</strong> accounts for IDX-specific market microstructure: tick size rules (IDR 1-25 depending on price level), lot size constraints (100 shares), and auto-rejection price limits. Transaction costs are modeled at 0.15% for buys and 0.25% for sells (including 0.1% final income tax). T+2 settlement is enforced for capital availability calculations.
            </p>
          </section>

          <section id="risk-metrics" className="mt-16">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Risk Metrics</h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Portfolio risk is quantified using both parametric and historical methods. The two primary metrics are Value at Risk (VaR) and Conditional Value at Risk (CVaR).
            </p>
            <div className="mt-4 space-y-3">
              <div className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] px-4 py-3">
                <code className="font-mono text-sm text-[var(--text-primary)]">VaR(alpha) = -mu - sigma * z(alpha)</code>
              </div>
              <div className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] px-4 py-3">
                <code className="font-mono text-sm text-[var(--text-primary)]">CVaR(alpha) = -mu + sigma * phi(z(alpha)) / alpha</code>
              </div>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              Where mu is the portfolio mean return, sigma is the portfolio standard deviation, z(alpha) is the standard normal quantile at confidence level alpha, and phi is the standard normal density function. We compute both metrics at 95% and 99% confidence levels on a daily and weekly horizon.
            </p>
          </section>

          <section id="execution" className="mt-16 pb-20">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Execution Algorithms</h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Pyhron provides two primary execution algorithms optimized for IDX liquidity profiles:
            </p>
            <div className="mt-4 space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">VWAP (Volume-Weighted Average Price)</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                  Slices parent orders into child orders proportional to historical intraday volume curves. The algorithm uses the previous 20-day average volume profile to distribute execution across both trading sessions, minimizing market impact for large orders.
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">TWAP (Time-Weighted Average Price)</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                  Distributes child orders evenly across a specified time window. Useful for instruments with low or unpredictable intraday volume patterns. Includes randomization of slice timing to reduce predictability and information leakage.
                </p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              Both algorithms enforce IDX lot size and tick size constraints, respect auto-rejection price limits, and integrate with the pre-trade risk engine for real-time position and exposure checks.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
