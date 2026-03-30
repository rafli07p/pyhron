import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Terms of Service' };

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary">Terms of Service</h1>
      <div className="mt-8 space-y-6 text-text-secondary text-sm leading-relaxed">
        <p>Last updated: March 2026</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">1. Acceptance of Terms</h2>
        <p>By accessing and using the Pyhron platform, you agree to be bound by these Terms of Service. Pyhron provides quantitative analytics, algorithmic trading tools, and market data for the Indonesia Stock Exchange (IDX).</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">2. Service Description</h2>
        <p>Pyhron offers factor models, stock screening, backtesting, paper trading, and live trading capabilities. Market data is sourced from IDX and third-party providers. Historical data availability depends on your subscription tier.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">3. Investment Disclaimer</h2>
        <p>Pyhron is a technology platform providing analytical tools. Nothing on this platform constitutes investment advice. Past performance of any strategy or factor model does not guarantee future results. Users are solely responsible for their investment decisions.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">4. API Usage</h2>
        <p>API access is subject to rate limits based on your subscription tier. Automated trading through the API is permitted within the bounds of IDX regulations and your brokerage agreement.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">5. Account Security</h2>
        <p>Users are responsible for maintaining the confidentiality of their account credentials. Accounts are locked after 5 failed login attempts for 15 minutes. Report unauthorized access immediately to security@pyhron.com.</p>
      </div>
    </div>
  );
}
