import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function ArticleDetailPage({ params }: Props) {
  const { slug } = await params;

  return (
    <div className="mx-auto max-w-3xl space-y-3">
      <Link
        href="/research/articles"
        className="inline-flex items-center gap-1 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Articles
      </Link>

      <PageHeader
        title={slug
          .replace(/-/g, ' ')
          .replace(/\b\w/g, (c) => c.toUpperCase())}
        description="Pyhron Research"
      />

      <div className="flex items-center gap-3 text-xs text-[var(--text-tertiary)]">
        <span>March 15, 2025</span>
        <span>12 min read</span>
        <Badge variant="outline">Factor</Badge>
        <Badge variant="outline">Momentum</Badge>
      </div>

      <Card>
        <CardContent className="prose prose-invert max-w-none p-4">
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
            This research article analyzes the performance of momentum-based strategies
            in the Indonesian stock market (IDX) during Q1 2025. Our findings indicate
            that 12-month momentum with 1-month reversal exclusion continues to generate
            significant risk-adjusted returns for IDX large-cap equities.
          </p>
          <h2 className="mt-6 text-lg font-semibold text-[var(--text-primary)]">Methodology</h2>
          <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
            We construct momentum portfolios using a universe of LQ45 constituents,
            sorting stocks into quintiles based on trailing 12-month returns excluding
            the most recent month. Portfolios are rebalanced monthly with IDX lot size
            constraints and realistic transaction cost assumptions (buy: 0.15%, sell: 0.25%).
          </p>
          <h2 className="mt-6 text-lg font-semibold text-[var(--text-primary)]">Key Findings</h2>
          <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
            The long-short momentum portfolio generated an annualized return of 18.4%
            with a Sharpe ratio of 1.84 during the analysis period. The long-only
            quintile 5 (highest momentum) outperformed IHSG by 8.2% on a risk-adjusted
            basis after accounting for all transaction costs and market impact.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
