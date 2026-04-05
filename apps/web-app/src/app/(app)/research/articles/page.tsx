import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import Link from 'next/link';

export const metadata = { title: 'Research Articles' };

const MOCK_ARTICLES = [
  {
    slug: 'idx-momentum-factor-q1-2025',
    title: 'IDX Momentum Factor: Q1 2025 Analysis',
    excerpt: 'We examine risk-adjusted returns of momentum strategies across IDX large caps, finding that 12-month momentum with 1-month reversal exclusion continues to generate significant alpha...',
    date: '2025-03-15',
    author: 'Pyhron Research',
    tags: ['Factor', 'Momentum'],
    readingTime: '12 min',
  },
  {
    slug: 'banking-sector-pairs-trading',
    title: 'Banking Sector Pairs Trading Opportunities',
    excerpt: 'Statistical cointegration analysis of IDX banking stocks reveals several pair trading opportunities with mean-reversion characteristics suitable for automated execution...',
    date: '2025-03-12',
    author: 'Pyhron Research',
    tags: ['Strategy', 'Pairs'],
    readingTime: '8 min',
  },
  {
    slug: 'ml-signal-validation-walk-forward',
    title: 'ML Signal Validation: Walk-Forward Results',
    excerpt: 'Walk-forward validation of our ensemble ML signal generator shows consistent out-of-sample performance with information ratio of 1.42 over the 2023-2025 period...',
    date: '2025-03-08',
    author: 'Pyhron Research',
    tags: ['ML', 'Validation'],
    readingTime: '15 min',
  },
  {
    slug: 'idx-small-cap-anomaly',
    title: 'IDX Small Cap Anomaly: Size Factor Deep Dive',
    excerpt: 'Our analysis of IDX size factor returns reveals a persistent small-cap premium after controlling for liquidity, with implications for portfolio construction...',
    date: '2025-03-01',
    author: 'Pyhron Research',
    tags: ['Factor', 'Size'],
    readingTime: '10 min',
  },
  {
    slug: 'volatility-regime-detection-hmm',
    title: 'Volatility Regime Detection with Hidden Markov Models',
    excerpt: 'Application of HMM-based regime detection to IHSG reveals three distinct volatility regimes. Strategy adaptation based on regime signals improves Sharpe by 0.35...',
    date: '2025-02-25',
    author: 'Pyhron Research',
    tags: ['ML', 'Volatility'],
    readingTime: '18 min',
  },
];

export default function ArticlesPage() {
  return (
    <div className="space-y-3">
      <PageHeader title="Research Articles" description="Published quantitative research and analysis" />

      <div className="space-y-4">
        {MOCK_ARTICLES.map((article) => (
          <Link key={article.slug} href={`/research/articles/${article.slug}`}>
            <Card className="p-3 transition-colors hover:border-[var(--accent-500)]">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    {article.title}
                  </h3>
                  <p className="mt-1 line-clamp-2 text-xs text-[var(--text-secondary)]">
                    {article.excerpt}
                  </p>
                  <div className="mt-3 flex items-center gap-3 text-xs text-[var(--text-tertiary)]">
                    <span>{article.date}</span>
                    <span>{article.readingTime}</span>
                    <span>{article.author}</span>
                  </div>
                </div>
                <div className="flex gap-1.5">
                  {article.tags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
