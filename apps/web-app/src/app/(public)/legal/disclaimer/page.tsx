export const metadata = { title: 'Investment Disclaimer' };

export default function DisclaimerPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Investment Disclaimer</h1>
      <p className="mt-2 text-sm text-[var(--text-tertiary)]">Last updated: March 1, 2026</p>

      <div className="mt-6 rounded-lg border border-[var(--warning)]/30 bg-[var(--warning)]/5 p-4 text-sm font-medium text-[var(--warning)]">
        Pyhron is NOT registered with the Indonesian Financial Services Authority (OJK) or the Indonesia Stock Exchange (IDX) as a broker-dealer, investment adviser, or securities intermediary.
      </div>

      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">1. Not Investment Advice</h2>
        <p>Nothing on this platform constitutes investment advice, financial guidance, or a recommendation to buy or sell any security. All content, signals, and analytics are provided strictly for informational and educational purposes.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">2. Risk of Loss</h2>
        <p>Trading in securities involves substantial risk and may result in the loss of your entire invested capital. You should only invest money that you can afford to lose entirely. Leveraged and derivative products carry additional risk.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">3. Past Performance</h2>
        <p>Past performance of any strategy, signal, or backtest presented on this platform is not indicative of future results. Historical simulations are based on past data and cannot account for future market conditions, liquidity changes, or regulatory shifts.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">4. Regulatory Status (OJK)</h2>
        <p>Pyhron operates as a technology and research platform, not a financial institution. We are not licensed, regulated, or supervised by OJK. Users are solely responsible for ensuring their trading activities comply with applicable regulations.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">5. Third-Party Data</h2>
        <p>Market data, financial statements, and other information are sourced from third-party providers. While we strive for accuracy, we do not guarantee the completeness or reliability of any third-party data. Data may be delayed or contain errors.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">6. Algorithmic Trading Risks</h2>
        <p>Algorithmic strategies may malfunction, execute unintended trades, or behave unpredictably during extreme market conditions. System failures, connectivity issues, and software bugs can result in significant financial losses.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">7. Paper Trading Limitations</h2>
        <p>Paper trading simulations do not account for real-world factors such as slippage, partial fills, market impact, or broker-specific execution delays. Simulated results will differ materially from live trading performance.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">8. Tax Considerations</h2>
        <p>Users are responsible for all tax obligations arising from their trading activities, including capital gains tax under Indonesian tax law (UU PPh). Pyhron does not provide tax advice and you should consult a qualified tax professional.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">9. Limitation of Liability</h2>
        <p>Pyhron, its officers, and affiliates shall not be held liable for any trading losses, data inaccuracies, or damages arising from reliance on information provided through the platform. You assume full responsibility for your investment decisions.</p>
      </div>
    </div>
  );
}
