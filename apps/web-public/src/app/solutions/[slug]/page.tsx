import type { Metadata } from 'next';
import Link from 'next/link';

const solutionData: Record<string, { title: string; description: string; features: string[]; useCases: string[] }> = {
  'factor-models': {
    title: 'Factor Models',
    description: 'Fama-French five-factor decomposition adapted for IDX equities. Compute value, momentum, quality, size, and low-volatility factors across 50+ stocks.',
    features: ['Five-factor decomposition (MktRf, SMB, HML, RMW, CMA)', 'Monthly rebalancing with IDX-specific adjustments', 'Factor exposure analysis per stock', 'Historical factor returns (10 years)', 'Custom factor weighting'],
    useCases: ['Asset managers building factor-tilted portfolios', 'Research teams analyzing factor premia in Indonesian markets', 'Risk managers decomposing portfolio returns'],
  },
  'risk-analytics': {
    title: 'Risk Analytics',
    description: 'Real-time portfolio risk monitoring with VaR (95/99%), stress testing, and automated kill-switch protection.',
    features: ['Parametric and historical VaR (1-day, 5-day)', 'Component VaR by position', 'Stress testing with historical scenarios', 'Drawdown monitoring with kill-switch', 'Sector concentration limits'],
    useCases: ['Portfolio managers monitoring daily risk exposure', 'Compliance teams enforcing risk limits', 'Algorithmic traders setting automated stop-losses'],
  },
  'portfolio-optimizer': {
    title: 'Portfolio Optimizer',
    description: 'Mean-variance and Black-Litterman optimization for IDX equities with realistic constraints.',
    features: ['Mean-variance optimization', 'Black-Litterman with analyst views', 'Sector and position constraints', 'Transaction cost modeling', 'Rebalancing schedule optimization'],
    useCases: ['Fund managers constructing optimal portfolios', 'Wealth advisors building model portfolios', 'Institutional investors with mandate constraints'],
  },
  'ai-insights': {
    title: 'AI Insights',
    description: 'Machine learning-driven alpha signals and anomaly detection for IDX equities.',
    features: ['ML-based alpha signal generation', 'Anomaly detection in trading patterns', 'Sentiment analysis from news feeds', 'Earnings surprise prediction', 'Feature importance explainability'],
    useCases: ['Quantitative traders incorporating ML signals', 'Research teams exploring alternative data', 'Risk managers detecting unusual market behavior'],
  },
  'strategy-marketplace': {
    title: 'Strategy Marketplace',
    description: '5 pre-built quantitative strategies with full backtesting history and live paper trading.',
    features: ['IDX Momentum (12-1 month)', 'Value-Quality composite', 'Pairs trading (banking sector)', 'Low-volatility income', 'Mean reversion intraday'],
    useCases: ['Retail quants looking for tested strategies', 'Fund managers evaluating systematic approaches', 'Educators teaching algorithmic trading'],
  },
  'backtesting-engine': {
    title: 'Backtesting Engine',
    description: 'Event-driven backtesting with IDX market structure: T+2 settlement, lot sizes, and realistic commission costs.',
    features: ['Event-driven architecture', 'T+2 settlement simulation', '100-share lot size handling', 'Realistic commission (0.15% buy, 0.25% sell)', 'Multiple performance metrics (Sharpe, Sortino, Calmar)'],
    useCases: ['Strategy developers testing new ideas', 'Risk managers stress-testing strategies', 'Academic researchers running empirical studies'],
  },
  'execution-algos': {
    title: 'Execution Algos',
    description: 'TWAP, VWAP, and adaptive execution algorithms designed for IDX liquidity profiles.',
    features: ['TWAP (Time-Weighted Average Price)', 'VWAP (Volume-Weighted Average Price)', 'Adaptive execution based on order book', 'Participation rate targeting', 'Real-time slippage monitoring'],
    useCases: ['Institutional traders minimizing market impact', 'Fund managers executing large rebalances', 'Algorithmic traders optimizing entry/exit'],
  },
  'live-terminal': {
    title: 'Live Terminal',
    description: 'Real-time trading terminal with WebSocket streaming, order management, and position monitoring.',
    features: ['Real-time price streaming', 'Order entry and management', 'Position and P&L monitoring', 'Strategy enable/disable controls', 'Kill-switch protection'],
    useCases: ['Active traders monitoring live positions', 'Fund managers overseeing strategy execution', 'Risk managers with real-time dashboards'],
  },
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const solution = solutionData[slug];
  return {
    title: solution?.title || 'Solution',
    description: solution?.description || 'Pyhron solution',
  };
}

export function generateStaticParams() {
  return Object.keys(solutionData).map((slug) => ({ slug }));
}

export default async function SolutionPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const solution = solutionData[slug];

  if (!solution) {
    return (
      <div className="mx-auto max-w-content px-6 py-16 text-center">
        <h1 className="font-display text-3xl text-text-primary">Solution not found</h1>
        <Link href="/" className="mt-4 inline-block text-accent-500 hover:text-accent-600">Back to home</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <div className="max-w-3xl">
        <h1 className="font-display text-4xl text-text-primary md:text-5xl">{solution.title}</h1>
        <p className="mt-6 text-lg text-text-secondary">{solution.description}</p>
      </div>

      <section className="mt-16">
        <h2 className="text-xl font-medium text-text-primary">Features</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {solution.features.map((feature) => (
            <div key={feature} className="flex gap-3 rounded-lg border border-border bg-bg-secondary p-4">
              <div className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full bg-accent-500" />
              <span className="text-sm text-text-secondary">{feature}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-16">
        <h2 className="text-xl font-medium text-text-primary">Use Cases</h2>
        <div className="mt-6 space-y-3">
          {solution.useCases.map((uc) => (
            <div key={uc} className="rounded-lg border border-border p-4">
              <p className="text-sm text-text-secondary">{uc}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-16">
        <Link
          href="/register"
          className="rounded-md bg-accent-500 px-8 py-3 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
        >
          Get Started
        </Link>
      </div>
    </div>
  );
}
