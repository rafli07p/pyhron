import Link from 'next/link';

export const metadata = { title: 'Data & Analytics' };

const features = [
  {
    title: 'Market Data',
    desc: 'Real-time and historical IDX data for 800+ instruments including equities, fixed income, and derivatives.',
    href: '/data/market-data',
  },
  {
    title: 'Fundamental Data',
    desc: 'Financial statements, valuation ratios, and corporate actions for every listed company on the IDX.',
    href: '/data/fundamentals',
  },
  {
    title: 'Alternative Data',
    desc: 'Sentiment analysis, fund flows, and macro indicators to complement traditional financial data.',
    href: '/data/macro',
  },
];

export default function DataPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Data & Analytics</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Comprehensive data solutions for Indonesian capital markets. From real-time prices to alternative datasets, everything you need to power quantitative research.
          </p>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div key={f.title} className="rounded-xl border border-black/[0.08] p-6">
                <h3 className="text-base font-semibold text-black">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-black/50">{f.desc}</p>
                <Link href={f.href} className="mt-4 inline-block text-sm font-medium text-[#2563eb] hover:text-[#1d4ed8]">
                  Learn more &rarr;
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="text-2xl font-bold text-black">Ready to explore our data?</h2>
          <p className="mt-2 text-sm text-black/50">Contact our team to learn more about our data solutions.</p>
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">
            Get in touch
          </Link>
        </div>
      </section>
    </div>
  );
}
