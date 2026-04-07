import Link from 'next/link';

const articles = [
  {
    category: 'Factor Research',
    title: 'Fama-French Five-Factor Model Applied to IDX LQ45',
    date: 'March 2026',
    excerpt:
      'We apply the Fama-French five-factor model to Indonesian large-cap equities, finding statistically significant value and profitability premiums after adjusting for IDX microstructure.',
    href: '/research/articles/fama-french-idx-lq45',
  },
  {
    category: 'Strategy',
    title: 'Pairs Trading in Indonesian Banking Sector: A Cointegration Approach',
    date: 'February 2026',
    excerpt:
      'Statistical cointegration analysis of BBCA-BMRI and BBRI-BBNI pairs reveals mean-reverting spreads with half-lives suitable for automated execution strategies.',
    href: '/research/articles/banking-sector-pairs-trading',
  },
  {
    category: 'Commodity Linkage',
    title: 'CPO Price Transmission and JPFA/MAIN Correlation Analysis',
    date: 'January 2026',
    excerpt:
      'Examining the transmission mechanism between crude palm oil futures and IDX poultry sector equities using Granger causality and impulse response functions.',
    href: '/research/articles/cpo-correlation-analysis',
  },
];

export function ResearchPreview() {
  return (
    <section className="bg-[#0A1628] py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#C9A84C]">
              Research & Insights
            </p>
            <h2 className="mt-4 text-3xl font-normal tracking-tight text-white lg:text-4xl">
              Latest publications
            </h2>
          </div>
          <Link
            href="/research/articles"
            className="hidden text-sm font-medium text-white/60 transition-colors hover:text-[#C9A84C] md:block"
          >
            View All &rarr;
          </Link>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {articles.map((article) => (
            <Link
              key={article.title}
              href={article.href}
              className="group border border-white/10 p-6 transition-colors hover:border-[#C9A84C]/40"
            >
              <span className="text-[10px] font-medium uppercase tracking-[0.15em] text-[#C9A84C]">
                {article.category}
              </span>
              <h3 className="mt-3 text-base font-medium leading-snug text-white group-hover:text-[#E8C97A]">
                {article.title}
              </h3>
              <p className="mt-3 text-xs leading-relaxed text-white/50">{article.excerpt}</p>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-[11px] text-white/40">{article.date}</span>
                <span className="text-xs font-medium text-white/60 transition-colors group-hover:text-[#C9A84C]">
                  Read More &rarr;
                </span>
              </div>
            </Link>
          ))}
        </div>

        <Link
          href="/research/articles"
          className="mt-8 block text-center text-sm font-medium text-white/60 transition-colors hover:text-[#C9A84C] md:hidden"
        >
          View All Research &rarr;
        </Link>
      </div>
    </section>
  );
}
