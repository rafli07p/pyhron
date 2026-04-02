export const metadata = { title: 'Methodology' };

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Methodology</h1>
      <div className="mt-8 space-y-6 text-sm leading-relaxed text-[var(--text-secondary)]">
        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Data Collection</h2>
          <p className="mt-2">We source IDX market data from multiple providers including EODHD (primary), yfinance (fallback), and direct exchange feeds. All data passes through validation pipelines ensuring completeness, consistency, and accuracy.</p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Signal Generation</h2>
          <p className="mt-2">Our ML pipeline uses ensemble models including XGBoost, LightGBM, and LSTM networks to generate trading signals. Each signal includes a confidence score and expected return estimate. Models are retrained weekly with walk-forward validation.</p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Risk Management</h2>
          <p className="mt-2">All orders pass through our pre-trade risk engine which enforces position limits, sector concentration caps, daily loss limits, and VaR constraints. A circuit breaker automatically halts all trading if predefined risk thresholds are breached.</p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Backtesting</h2>
          <p className="mt-2">Our backtesting engine accounts for IDX-specific rules including T+2 settlement, lot size constraints (100 shares), tick size rules, and realistic commission/tax estimates (0.15% buy, 0.25% sell including 0.1% final income tax).</p>
        </section>
        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">IDX Market Rules</h2>
          <ul className="mt-2 list-inside list-disc space-y-1">
            <li>Lot size: 100 shares</li>
            <li>Tick sizes: IDR 1 (≤200), IDR 2 (≤500), IDR 5 (≤2,000), IDR 10 (≤5,000), IDR 25 (&gt;5,000)</li>
            <li>Trading hours: Session I (09:00-11:30), Session II (13:30-15:00) WIB</li>
            <li>Settlement: T+2</li>
            <li>No short selling</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
