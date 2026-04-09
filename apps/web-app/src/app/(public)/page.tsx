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
      {/* Hero — full viewport, pulled up behind fixed header */}
      <div className="-mt-[88px]">
        <HeroSection />
      </div>

      {/* Trust Metrics */}
      <section className="border-t border-black/[0.06] bg-white py-16">
        <ScrollReveal preset="fadeUp" stagger={0.15} className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-6 lg:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <CountUp
                end={s.end}
                prefix={s.prefix}
                suffix={s.suffix}
                decimals={s.decimals}
                className="text-4xl font-mono font-semibold text-black"
              />
              <p className="mt-2 text-sm text-black/50">{s.label}</p>
            </div>
          ))}
        </ScrollReveal>
      </section>

      {/* Trusted By / Data Partners */}

      {/* Platform Capabilities */}
      <section className="bg-white py-24">
        <div className="mx-auto max-w-6xl px-6">
          <ScrollReveal>
            <h2 className="text-2xl font-normal tracking-tight text-black">
              Platform Capabilities
            </h2>
            <p className="mt-2 max-w-lg text-sm text-black/50">
              Everything you need for systematic investing in Indonesian markets
            </p>
          </ScrollReveal>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((cap, i) => (
              <ScrollReveal key={cap.title} preset="fadeUp" delay={i * 0.1}>
                <div className="group rounded-lg border border-black/[0.06] bg-white p-6 transition-all duration-200 hover:-translate-y-1 hover:border-[#2563eb]/30 hover:shadow-md">
                  <cap.icon className="h-7 w-7 text-[#2563eb]" strokeWidth={1.5} />
                  <h3 className="mt-4 text-sm font-semibold text-black">{cap.title}</h3>
                  <p className="mt-2 text-sm text-black/50">{cap.desc}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* Research Previews */}
      <section className="border-t border-black/[0.06] bg-[#f9f9f9] py-24">
        <div className="mx-auto max-w-6xl px-6">
          <ScrollReveal>
            <h2 className="text-2xl font-normal tracking-tight text-black">
              Latest Research
            </h2>
          </ScrollReveal>
          <ScrollReveal preset="fadeUp" stagger={0.15} className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
            {articles.map((article) => (
              <Link
                key={article.title}
                href={article.href}
                className="group rounded-lg border border-black/[0.06] bg-white p-5 transition-all hover:border-[#2563eb]/30 hover:shadow-md"
              >
                <span className="text-[10px] font-medium uppercase tracking-wider text-[#2563eb]">
                  {article.tag}
                </span>
                <h3 className="mt-2 text-sm font-medium leading-snug text-black group-hover:text-[#2563eb]">
                  {article.title}
                </h3>
                <span className="mt-3 block text-xs text-black/40">Read More &rarr;</span>
              </Link>
            ))}
          </ScrollReveal>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-white py-20 text-center">
        <ScrollReveal>
          <h2 className="text-2xl font-normal text-black">
            Ready to elevate your research?
          </h2>
          <div className="mt-6 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-full bg-[#2563eb] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8]"
            >
              Create Free Account &rarr;
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 rounded-full border border-black/15 px-6 py-3 text-sm font-medium text-black/60 transition-colors hover:text-black"
            >
              Schedule Demo &rarr;
            </Link>
          </div>
        </ScrollReveal>
      </section>

      <FinancialDisclaimer className="border-t border-black/[0.06] bg-[#f5f5f5] px-6 py-6" />
    </>
  );
}
