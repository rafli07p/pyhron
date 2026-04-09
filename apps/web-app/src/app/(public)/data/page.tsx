import Link from 'next/link';

export const metadata = { title: 'Data & Analytics' };

const solutions = [
  { title: 'Extensive data', desc: 'Access a diverse range of historical, real-time, and reference data covering 800+ IDX instruments across equities, fixed income, and derivatives.', href: '/data/market-data' },
  { title: 'Advanced analytics', desc: 'Leverage in-depth analytical tools and factor models designed to support portfolio construction, risk management, and alpha generation.', href: '/data/factors' },
  { title: 'Custom solutions', desc: 'Customize your analytics and data to meet the specific needs of your investment process, from factor construction to signal generation.', href: '/contact' },
];

const products = [
  { title: 'Market Data', desc: 'Real-time and end-of-day pricing for the complete IDX universe', href: '/data/market-data' },
  { title: 'Factor Models', desc: '18 proprietary alpha factors across momentum, value, quality, and volatility', href: '/data/factors' },
  { title: 'Fundamental Data', desc: 'Financial statements, ratios, and corporate actions for every listed company', href: '/data/fundamentals' },
  { title: 'Technical Signals', desc: '30+ technical indicators with backtesting integration and custom formulas', href: '/data/technicals' },
  { title: 'ML-Driven Signals', desc: 'Ensemble machine learning models with confidence scoring and factor attribution', href: '/data/ml-signals' },
  { title: 'Macro & Economic', desc: 'BI rate, inflation, GDP, commodity prices, and exchange rate data for Indonesia', href: '/data/macro' },
];

export default function DataPage() {
  return (
    <div className="bg-white">
      {/* Hero — MSCI style: blue title, grey subtitle */}
      <section className="bg-[#eef2ff] py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-4xl font-bold text-[#2563eb] md:text-5xl">Data & Analytics</h1>
          <p className="mt-4 max-w-2xl text-2xl font-normal text-black/40 md:text-3xl">
            Powering better investment decisions
          </p>
        </div>
      </section>

      {/* Driving strategic decision making */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-[#2563eb] md:text-3xl">Driving strategic decision making</h2>
          <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-black/60">
            Explore premium data and advanced analytics designed to give you a clearer view of the Indonesian
            markets and power better decisions across strategies and asset classes.
          </p>

          <div className="mt-16 grid grid-cols-1 gap-12 md:grid-cols-3">
            {solutions.map((s) => (
              <div key={s.title}>
                {/* Placeholder icon circle */}
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border-2 border-[#2563eb]/20">
                  <div className="h-8 w-8 rounded-full border-2 border-[#2563eb]/30" />
                </div>
                <h3 className="text-xl font-bold text-black">{s.title}</h3>
                <p className="mt-3 text-[14px] leading-relaxed text-black/50">{s.desc}</p>
                <Link href={s.href} className="mt-4 inline-block text-[14px] font-medium text-[#2563eb] hover:underline">
                  Learn more &rarr;
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Products grid */}
      <section className="border-t border-black/[0.06] bg-[#f9fafb] py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-black">Our data products</h2>
          <p className="mt-2 text-[15px] text-black/50">End-to-end tools to meet your needs</p>
          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {products.map((p) => (
              <Link key={p.title} href={p.href} className="group rounded-xl border border-black/[0.08] bg-white p-6 transition-all hover:border-[#2563eb]/30 hover:shadow-md">
                <h3 className="text-base font-semibold text-black group-hover:text-[#2563eb]">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-black/50">{p.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="text-2xl font-bold text-black">Ready to explore our data?</h2>
          <p className="mt-2 text-sm text-black/50">Contact our team for a personalized demo.</p>
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">
            Get in touch
          </Link>
        </div>
      </section>
    </div>
  );
}
