import Link from 'next/link';

export const metadata = { title: 'Research & Insights' };

const themes = [
  { title: 'Quantitative Strategies', desc: 'Momentum, factor investing, and statistical arbitrage research for Indonesian markets.', href: '/research-and-insights/quant' },
  { title: 'Machine Learning', desc: 'Ensemble models, deep learning, and ML-driven signal generation for IDX.', href: '/research-and-insights/ml' },
  { title: 'Risk Management', desc: 'VaR, stress testing, and portfolio risk analytics for Indonesian portfolios.', href: '/research-and-insights/risk' },
  { title: 'Macro & Economic', desc: 'BI rate analysis, inflation monitoring, and currency dynamics research.', href: '/research-and-insights/macro' },
];

const articles = [
  { title: 'IDX Factor Models Under Stress', desc: 'The AI-driven equity rotation that rattled developed markets earlier this year also exposed a fault line in IDX factor premia.', slug: 'idx-factor-stress-test' },
  { title: 'US–China Tensions Reshape IDX Foreign Flows', desc: 'It may be time to reassess currency-hedged exposure as portfolio reallocations flip historical beta relationships.', slug: 'us-china-idx-flows' },
  { title: 'IDX Liquidity Premium', desc: 'Could volatility measures signal a coming dislocation in second-board Indonesian equities?', slug: 'idx-liquidity-premium' },
];

export default function ResearchAndInsightsPage() {
  return (
    <div className="bg-white">
      <section className="bg-[#eef2ff] py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-4xl font-bold text-[#2563eb] md:text-5xl">Research & Insights</h1>
          <p className="mt-4 max-w-2xl text-2xl font-normal text-black/40 md:text-3xl">
            Stay ahead of changing markets
          </p>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-[#2563eb] md:text-3xl">Research by theme</h2>
          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {themes.map((t) => (
              <Link key={t.title} href={t.href} className="group rounded-xl border border-black/[0.08] bg-white p-6 transition-all hover:border-[#2563eb]/30 hover:shadow-md">
                <h3 className="text-base font-semibold text-black group-hover:text-[#2563eb]">{t.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-black/50">{t.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-black/[0.06] bg-[#f9fafb] py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-black">Latest articles</h2>
          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
            {articles.map((a) => (
              <Link key={a.slug} href={`/research-and-insights/articles/${a.slug}`} className="group rounded-xl border border-black/[0.08] bg-white p-6 transition-all hover:border-[#2563eb]/30 hover:shadow-md">
                <h3 className="text-base font-semibold text-black group-hover:text-[#2563eb]">{a.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-black/50">{a.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="text-2xl font-bold text-black">Ready to explore our research?</h2>
          <p className="mt-2 text-sm text-black/50">Contact our team for a personalized demo.</p>
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">
            Get in touch
          </Link>
        </div>
      </section>
    </div>
  );
}
