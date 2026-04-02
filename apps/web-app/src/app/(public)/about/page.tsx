export const metadata = { title: 'About' };

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">About Pyhron</h1>
      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <p>
          Pyhron is an institutional-grade quantitative research and algorithmic trading platform
          built specifically for Indonesia&apos;s capital markets. We combine cutting-edge machine
          learning, robust data infrastructure, and professional-grade execution capabilities into
          a single coherent platform.
        </p>
        <p>
          Our mission is to democratize quantitative finance for the Indonesian market, providing
          tools previously available only to large institutional investors.
        </p>
        <h2 className="mt-8 text-xl font-semibold text-[var(--text-primary)]">Our Approach</h2>
        <p>
          We believe in systematic, evidence-based investing. Every signal, strategy, and decision
          on Pyhron is backed by rigorous quantitative analysis, proper backtesting methodology,
          and comprehensive risk management.
        </p>
        <h2 className="mt-8 text-xl font-semibold text-[var(--text-primary)]">Technology</h2>
        <p>
          Pyhron is built on an event-driven microservices architecture using Python, FastAPI,
          PostgreSQL with TimescaleDB, Apache Kafka, and PyTorch. Our frontend delivers a
          Bloomberg-like experience powered by Next.js and React.
        </p>
      </div>
    </div>
  );
}
