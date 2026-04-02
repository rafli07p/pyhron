export const metadata = { title: 'Terms of Service' };

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Terms of Service</h1>
      <p className="mt-2 text-sm text-[var(--text-tertiary)]">Last updated: March 2025</p>
      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <p>By using Pyhron, you agree to the following terms and conditions. Please read them carefully.</p>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">1. Service Description</h2>
        <p>Pyhron provides quantitative research tools, backtesting capabilities, and algorithmic trading functionality for the Indonesia Stock Exchange (IDX). The platform is designed for informational and research purposes.</p>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">2. No Investment Advice</h2>
        <p>Nothing on this platform constitutes investment advice, recommendation, or solicitation. All market data, signals, and analytics are provided for informational purposes only. Users are solely responsible for their trading decisions.</p>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">3. Risk Disclosure</h2>
        <p>Trading in securities involves substantial risk of loss. Past performance is not indicative of future results. Algorithmic trading strategies may experience significant drawdowns and may not be suitable for all investors.</p>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">4. Regulatory Status</h2>
        <p>Pyhron is NOT registered as a broker-dealer, investment adviser, or securities intermediary with the Indonesian Financial Services Authority (OJK) or the Indonesia Stock Exchange (IDX).</p>
      </div>
    </div>
  );
}
