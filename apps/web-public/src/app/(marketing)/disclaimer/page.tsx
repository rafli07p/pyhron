import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Disclaimer' };

export default function DisclaimerPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary">Disclaimer</h1>
      <div className="mt-8 space-y-6 text-text-secondary text-sm leading-relaxed">
        <p>Last updated: March 2026</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">Investment Risk</h2>
        <p>Trading securities involves substantial risk of loss. Past performance of any strategy, factor model, or index does not guarantee future results. The value of investments can go down as well as up.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">Not Investment Advice</h2>
        <p>Pyhron provides analytical tools and data. Nothing on this platform constitutes investment advice, solicitation, or recommendation to buy or sell any security. Users should consult with a licensed financial advisor before making investment decisions.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">Data Accuracy</h2>
        <p>While we strive for accuracy, market data and analytical outputs may contain errors or delays. Pyhron is not responsible for trading losses resulting from data inaccuracies or system outages.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">Regulatory Compliance</h2>
        <p>Users are responsible for ensuring their trading activities comply with applicable laws and regulations, including those of the Indonesia Financial Services Authority (OJK) and the Indonesia Stock Exchange (IDX).</p>
      </div>
    </div>
  );
}
