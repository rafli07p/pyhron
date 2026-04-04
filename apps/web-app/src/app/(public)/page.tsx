'use client';

import Link from 'next/link';
import { FlaskConical, Zap, Shield, Database, Brain, TrendingUp } from 'lucide-react';
import { HeroSection } from '@/components/hero/HeroSection';
import { ScrollReveal } from '@/components/motion/ScrollReveal';
import { CountUp } from '@/components/motion/CountUp';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

const stats = [
  { end: 15.2, prefix: 'IDR ', suffix: 'T', decimals: 1, label: 'Data Points' },
  { end: 800, prefix: '', suffix: '+', decimals: 0, label: 'IDX Instruments' },
  { end: 99.97, prefix: '', suffix: '%', decimals: 2, label: 'Uptime SLA' },
  { end: 50, prefix: '<', suffix: 'ms', decimals: 0, label: 'API p99' },
];

const capabilities = [
  { icon: FlaskConical, title: 'Quantitative Research', desc: 'ML signals, backtests, factor analysis, walk-forward optimization' },
  { icon: Zap, title: 'Algorithmic Execution', desc: 'VWAP, TWAP, paper & live via Alpaca. IDX lot size aware.' },
  { icon: Shield, title: 'Risk Analytics', desc: 'Parametric VaR, CVaR, stress testing, drawdown, factor exposure.' },
  { icon: Database, title: 'Data Platform', desc: 'yfinance, EODHD, Kafka streaming. Real-time and historical.' },
  { icon: Brain, title: 'ML Pipeline', desc: 'PyTorch, scikit-learn, MLflow tracking. Model registry and deployment.' },
  { icon: TrendingUp, title: 'Portfolio Management', desc: 'Real-time positions, performance attribution, rebalancing.' },
];

const articles = [
  { title: 'Fama-French Five-Factor Model Applied to IDX LQ45', tag: 'Factor Research', href: '/research/articles/fama-french-idx' },
  { title: 'Pairs Trading in Indonesian Banking Sector', tag: 'Strategy', href: '/research/articles/banking-pairs' },
  { title: 'CPO Price Transmission and JPFA/MAIN Correlation', tag: 'Commodity', href: '/research/articles/cpo-correlation' },
];

export default function LandingPage() {
  return (
    <>
      {/* Hero — pulled up behind the fixed header */}
      <div className="-mt-[88px]">
        <HeroSection />
      </div>

      {/* Trust Metrics */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-0)] py-24">
        <ScrollReveal preset="fadeUp" stagger={0.15} className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-6 lg:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <CountUp
                end={s.end}
                prefix={s.prefix}
                suffix={s.suffix}
                decimals={s.decimals}
                className="text-4xl font-mono font-semibold text-[var(--text-primary)]"
              />
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{s.label}</p>
            </div>
          ))}
        </ScrollReveal>
      </section>

      {/* Platform Capabilities */}
      <section className="bg-[var(--surface-0)] py-24">
        <div className="mx-auto max-w-6xl px-6">
          <ScrollReveal>
            <h2 className="text-2xl font-light tracking-tight text-[var(--text-primary)]">
              Platform Capabilities
            </h2>
            <p className="mt-2 max-w-lg text-sm text-[var(--text-secondary)]">
              Everything you need for systematic investing in Indonesian markets
            </p>
          </ScrollReveal>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((cap, i) => (
              <ScrollReveal key={cap.title} preset="fadeUp" delay={i * 0.1}>
                <div className="group rounded-lg border border-[var(--border-default)] p-6 transition-all duration-200 hover:-translate-y-1 hover:border-[var(--accent-500)] hover:shadow-lg hover:shadow-[var(--accent-500)]/5">
                  <cap.icon className="h-7 w-7 text-[var(--accent-500)]" strokeWidth={1.5} />
                  <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">{cap.title}</h3>
                  <p className="mt-2 text-sm text-[var(--text-tertiary)]">{cap.desc}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* Research Previews */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-1)] py-24">
        <div className="mx-auto max-w-6xl px-6">
          <ScrollReveal>
            <h2 className="text-2xl font-light tracking-tight text-[var(--text-primary)]">
              Latest Research
            </h2>
          </ScrollReveal>
          <ScrollReveal preset="fadeUp" stagger={0.15} className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
            {articles.map((article) => (
              <Link
                key={article.title}
                href={article.href}
                className="group rounded-lg border border-[var(--border-default)] p-5 transition-colors hover:border-[var(--accent-500)]"
              >
                <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--accent-500)]">
                  {article.tag}
                </span>
                <h3 className="mt-2 text-sm font-medium leading-snug text-[var(--text-primary)] group-hover:text-[var(--accent-500)]">
                  {article.title}
                </h3>
                <span className="mt-3 block text-xs text-[var(--text-tertiary)]">Read More &rarr;</span>
              </Link>
            ))}
          </ScrollReveal>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="border-t border-[var(--border-default)] bg-[var(--surface-0)] py-12">
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
      <section className="bg-[var(--surface-0)] py-20 text-center">
        <ScrollReveal>
          <h2 className="text-2xl font-light text-[var(--text-primary)]">
            Ready to elevate your research?
          </h2>
          <div className="mt-6 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-[var(--accent-500)] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
            >
              Create Free Account &rarr;
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 border border-[var(--border-default)] px-6 py-3 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              Schedule Demo &rarr;
            </Link>
          </div>
        </ScrollReveal>
      </section>

      <FinancialDisclaimer className="border-t border-[var(--border-default)] bg-[var(--surface-0)] px-6 py-6" />
    </>
  );
}
