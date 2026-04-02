import Link from 'next/link';
import { Button } from '@/design-system/primitives/Button';
import { Card } from '@/design-system/primitives/Card';
import { FlaskConical, Zap, Shield, Database, Brain, TrendingUp } from 'lucide-react';

export default function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative flex min-h-[80vh] flex-col items-center justify-center px-6 text-center">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />
        <div className="relative z-10 max-w-3xl">
          <h1 className="text-4xl font-bold tracking-tight text-[var(--text-primary)] sm:text-5xl lg:text-6xl">
            Institutional-Grade
            <br />
            Quantitative Research
            <br />
            <span className="text-[var(--accent-500)]">for Indonesia&apos;s Capital Markets</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-base text-[var(--text-secondary)] sm:text-lg">
            Pyhron unifies market data, ML-driven signal generation, backtesting, and live
            execution into a single coherent platform.
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Button size="lg" asChild>
              <Link href="/register">Start Research →</Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/methodology">View Methodology →</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Trust Metrics */}
      <section className="border-y border-[var(--border-default)] bg-[var(--surface-1)] py-12">
        <div className="mx-auto grid max-w-5xl grid-cols-2 gap-8 px-6 md:grid-cols-4">
          {[
            { value: 'IDR 15.2T', label: 'Data Points' },
            { value: '800+', label: 'IDX Stocks' },
            { value: '99.97%', label: 'Uptime SLA' },
            { value: '<50ms', label: 'API p99' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="tabular-nums text-2xl font-bold text-[var(--text-primary)] sm:text-3xl">{stat.value}</p>
              <p className="mt-1 text-sm text-[var(--text-tertiary)]">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-2xl font-bold text-[var(--text-primary)]">Platform Capabilities</h2>
          <p className="mx-auto mt-2 max-w-lg text-center text-sm text-[var(--text-secondary)]">
            Everything you need for systematic investing in Indonesian markets
          </p>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: FlaskConical, title: 'Quantitative Research', desc: 'ML signals, backtests, factor analysis, walk-forward optimization' },
              { icon: Zap, title: 'Algorithmic Execution', desc: 'VWAP, TWAP, paper & live via Alpaca. IDX lot size aware.' },
              { icon: Shield, title: 'Risk Analytics', desc: 'Parametric VaR, CVaR, stress testing, drawdown, factor exposure.' },
              { icon: Database, title: 'Data Platform', desc: 'yfinance, EODHD, Kafka streaming. Real-time and historical.' },
              { icon: Brain, title: 'ML Pipeline', desc: 'PyTorch, scikit-learn, MLflow tracking. Model registry and deployment.' },
              { icon: TrendingUp, title: 'Portfolio Management', desc: 'Real-time positions, performance attribution, rebalancing.' },
            ].map((cap) => (
              <Card key={cap.title} className="p-6">
                <cap.icon className="h-8 w-8 text-[var(--accent-500)]" />
                <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">{cap.title}</h3>
                <p className="mt-2 text-sm text-[var(--text-tertiary)]">{cap.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="border-y border-[var(--border-default)] bg-[var(--surface-1)] py-12">
        <div className="mx-auto max-w-5xl px-6">
          <p className="text-center text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            Built with
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-6 text-sm text-[var(--text-tertiary)]">
            {['Python', 'FastAPI', 'PostgreSQL', 'Kafka', 'PyTorch', 'Next.js', 'TypeScript', 'Redis'].map((tech) => (
              <span key={tech} className="font-mono">{tech}</span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 text-center">
        <h2 className="text-2xl font-bold text-[var(--text-primary)]">Ready to elevate your research?</h2>
        <div className="mt-6 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Button size="lg" asChild>
            <Link href="/register">Create Free Account →</Link>
          </Button>
          <Button variant="outline" size="lg" asChild>
            <Link href="/contact">Schedule Demo →</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
