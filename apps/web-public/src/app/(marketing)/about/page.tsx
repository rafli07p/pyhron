import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'About',
  description: 'Pyhron provides quantitative analytics and algorithmic trading solutions for the Indonesia Stock Exchange.',
};

const team = [
  { name: 'Rafli Perdana', role: 'Founder & Head of Quantitative Strategy', initials: 'RP' },
  { name: 'Arief Wibowo', role: 'Head of Engineering', initials: 'AW' },
  { name: 'Sarah Wijaya', role: 'Head of Research', initials: 'SW' },
  { name: 'Budi Santoso', role: 'Senior Quantitative Analyst', initials: 'BS' },
  { name: 'Diana Putri', role: 'Full-Stack Developer', initials: 'DP' },
  { name: 'Fajar Rahman', role: 'Data Engineer', initials: 'FR' },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">About Pyhron</h1>
      <div className="mt-8 max-w-3xl space-y-6 text-text-secondary">
        <p>
          Pyhron is a quantitative analytics and algorithmic trading platform built specifically for the Indonesia Stock Exchange (IDX). We provide institutional-quality factor models, backtesting infrastructure, and live trading capabilities to professional investors and retail quants.
        </p>
        <p>
          Our platform covers 50+ IDX equities with 500+ factor signals, 10 years of historical data, and 5 systematic trading strategies. We process real-time market data through WebSocket streaming and provide RESTful API access for programmatic integration.
        </p>
        <p>
          Founded in Jakarta, our team combines quantitative finance expertise with deep knowledge of Indonesian capital markets, including IDX microstructure (T+2 settlement, lot sizes, price tick bands) and local regulatory requirements.
        </p>
      </div>

      <section className="mt-20">
        <h2 className="font-display text-3xl text-text-primary">Our Team</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {team.map((member) => (
            <div key={member.name} className="rounded-lg border border-border bg-bg-secondary p-6">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-500/10 text-lg font-medium text-accent-500">
                {member.initials}
              </div>
              <h3 className="mt-4 font-medium text-text-primary">{member.name}</h3>
              <p className="mt-1 text-sm text-text-secondary">{member.role}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-20">
        <h2 className="font-display text-3xl text-text-primary">Methodology</h2>
        <div className="mt-8 max-w-3xl space-y-4 text-text-secondary">
          <p>
            Our factor models follow the Fama-French framework adapted for Indonesian market characteristics. We compute value (E/P, B/P), momentum (12-1 month), quality (ROE, accruals), size (market cap), and low-volatility (realized vol) factors on a monthly rebalancing schedule.
          </p>
          <p>
            Backtesting incorporates realistic IDX constraints: T+2 settlement, 100-share lot sizes, price tick bands (Rp 1/2/5/10/25/50 depending on price level), and commission costs of 0.15% buy / 0.25% sell (including tax).
          </p>
        </div>
      </section>
    </div>
  );
}
