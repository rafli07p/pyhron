import { ResearchCard } from '@/components/research/ResearchCard';
import { mockArticles } from '@/lib/mock/data/research';

export function InsightsSection() {
  const latestArticles = mockArticles.slice(0, 3);

  return (
    <section className="bg-bg-primary py-24 md:py-32">
      <div className="mx-auto max-w-content px-6">
        <h2 className="font-display text-3xl text-text-primary md:text-4xl">
          Latest Research
        </h2>
        <p className="mt-4 text-text-secondary">
          Quantitative research, market commentary, and factor analysis for IDX.
        </p>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {latestArticles.map((article) => (
            <ResearchCard
              key={article.slug}
              title={article.title}
              slug={article.slug}
              excerpt={article.excerpt}
              category={article.category}
              date={article.date}
              readTime={article.readTime}
              coverImage={article.coverImage}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
