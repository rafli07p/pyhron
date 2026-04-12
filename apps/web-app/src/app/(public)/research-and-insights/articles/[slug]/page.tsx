import Link from 'next/link';

const articlesData: Record<string, { title: string; desc: string; content: string }> = {
  'idx-factor-stress-test': {
    title: 'IDX Factor Models Under Stress',
    desc: 'The AI-driven equity rotation that rattled developed markets earlier this year also exposed a fault line in IDX factor premia. We examine the implications for Indonesia-focused quant portfolios.',
    content: 'This research examines how the AI-driven equity rotation that rattled developed markets also exposed vulnerabilities in Indonesian factor models. We analyze the performance of momentum, value, quality, and volatility factors during the stress period and provide recommendations for portfolio managers navigating these conditions.',
  },
  'us-china-idx-flows': {
    title: 'US–China Tensions Reshape IDX Foreign Flows',
    desc: 'It may be time to reassess currency-hedged exposure as portfolio reallocations flip historical beta relationships across Indonesian equities.',
    content: 'Geopolitical tensions between the US and China are creating significant shifts in foreign fund flows to Indonesian equities. This report analyzes the changing patterns of portfolio reallocations and their implications for currency-hedged strategies in the IDX market.',
  },
  'idx-liquidity-premium': {
    title: 'IDX Liquidity Premium',
    desc: 'Could volatility measures signal a coming dislocation in second-board Indonesian equities?',
    content: 'We examine the relationship between liquidity premiums and volatility in Indonesian equities, with particular focus on second-board instruments. Our analysis suggests that current volatility measures may be signaling a structural shift in liquidity dynamics.',
  },
};

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const article = articlesData[params.slug];

  if (!article) {
    return (
      <div className="bg-white py-20">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h1 className="text-3xl font-bold text-black">Article not found</h1>
          <Link href="/research-and-insights" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">
            Back to Research
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-4xl px-6">
          <Link href="/research-and-insights" className="text-sm text-[#2563eb] hover:underline">&larr; Back to Research & Insights</Link>
          <h1 className="mt-6 text-3xl font-bold text-black md:text-4xl">{article.title}</h1>
          <p className="mt-4 text-lg text-black/50">{article.desc}</p>
        </div>
      </section>
      <section className="py-16">
        <div className="mx-auto max-w-4xl px-6">
          <p className="text-[15px] leading-relaxed text-black/70">{article.content}</p>
        </div>
      </section>
    </div>
  );
}
