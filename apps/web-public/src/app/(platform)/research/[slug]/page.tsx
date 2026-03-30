import type { Metadata } from 'next';
import Link from 'next/link';
import { mockArticles } from '@/lib/mock/data/research';
import { formatDate } from '@/lib/utils/format';
import { ShareButtons } from '@/components/research/ShareButtons';

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const article = mockArticles.find((a) => a.slug === slug);
  return {
    title: article ? `${article.title} | Pyhron Research` : 'Research Article',
    description: article?.excerpt || 'Pyhron quantitative research article.',
    openGraph: article ? { images: [article.coverImage] } : undefined,
  };
}

export function generateStaticParams() {
  return mockArticles.map((a) => ({ slug: a.slug }));
}

export default async function ResearchArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const article = mockArticles.find((a) => a.slug === slug);

  if (!article) {
    return (
      <div className="mx-auto max-w-content px-6 py-16 text-center">
        <h1 className="font-display text-3xl">Article not found</h1>
        <Link href="/research" className="mt-4 inline-block text-accent-500">Back to Research</Link>
      </div>
    );
  }

  const related = mockArticles.filter((a) => a.slug !== slug && a.category === article.category).slice(0, 3);

  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <div className="grid gap-12 lg:grid-cols-[1fr_300px]">
        <article className="max-w-none">
          <div className="mb-8">
            <span className="rounded bg-accent-500/10 px-2 py-0.5 text-xs font-medium text-accent-500">
              {article.category.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </span>
            <h1 className="mt-4 font-display text-3xl text-text-primary md:text-4xl">
              {article.title}
            </h1>
            <div className="mt-4 flex items-center gap-4 text-sm text-text-muted">
              <span>{article.author.name}</span>
              <span>&middot;</span>
              <span>{formatDate(article.date)}</span>
              <span>&middot;</span>
              <span>{article.readTime} min read</span>
            </div>
          </div>

          <div className="aspect-video rounded-lg bg-bg-tertiary flex items-center justify-center text-text-muted mb-8">
            Cover Image Placeholder
          </div>

          <div className="prose prose-lg max-w-none text-text-secondary">
            <p>{article.excerpt}</p>
            <p>
              This is a placeholder for the full MDX content of the article. In production, this would be rendered
              via next-mdx-remote with KaTeX equations, Shiki code blocks, and embedded Recharts/D3 charts.
            </p>
            <h2>Methodology</h2>
            <p>
              The analysis uses daily return data from IDX for the period 2015-2025. Factor returns are computed
              following the Fama-French methodology with adjustments for IDX market structure including T+2 settlement
              and 100-share lot sizes.
            </p>
            <h2>Results</h2>
            <p>
              Our findings show persistent value and momentum premia in Indonesian equities, with the momentum factor
              delivering the highest risk-adjusted returns (Sharpe ratio of 0.82) over the sample period.
            </p>
            <h2>Conclusion</h2>
            <p>
              Factor investing in IDX offers meaningful diversification benefits compared to cap-weighted benchmarks.
              The results support systematic factor allocation strategies for institutional investors in Indonesia.
            </p>
          </div>

          <div className="mt-12 flex items-center gap-4 border-t border-border pt-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-500/10 text-accent-500 font-medium">
              {article.author.name.split(' ').map(w => w[0]).join('')}
            </div>
            <div>
              <p className="font-medium text-text-primary">{article.author.name}</p>
              <p className="text-sm text-text-secondary">{article.author.role}</p>
            </div>
          </div>
        </article>

        <aside className="hidden lg:block">
          <div className="sticky top-24 space-y-6">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted mb-3">
                Share
              </h3>
              <ShareButtons />
            </div>
            {related.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted mb-3">
                  Related
                </h3>
                <div className="space-y-3">
                  {related.map((r) => (
                    <Link key={r.slug} href={`/research/${r.slug}`} className="block rounded-lg border border-border p-3 hover:border-accent-500 transition-colors">
                      <p className="text-sm font-medium text-text-primary line-clamp-2">{r.title}</p>
                      <p className="mt-1 text-xs text-text-muted">{r.readTime} min read</p>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
