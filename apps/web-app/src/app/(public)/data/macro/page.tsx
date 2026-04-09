import Link from 'next/link';

export const metadata = { title: 'Macro & Economic Data' };

const features = [
  { title: 'BI Rate & Monetary Policy', desc: 'Bank Indonesia reference rate, reserve requirements, and policy meeting outcomes updated in real time.' },
  { title: 'Inflation & CPI', desc: 'Headline and core CPI, producer prices, and regional inflation breakdowns across Indonesian provinces.' },
  { title: 'GDP & Growth', desc: 'Quarterly GDP components, industrial production, and leading economic indicators for Indonesia.' },
  { title: 'Commodity Prices', desc: 'Palm oil, coal, nickel, tin, and other key Indonesian commodity benchmarks with full history.' },
  { title: 'Exchange Rates', desc: 'USD/IDR spot, NDF curves, and trade-weighted indexes critical for foreign investor analysis.' },
];

export default function MacroPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Macro & Economic Data</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Timely macroeconomic indicators and commodity data to inform top-down allocation and risk management for Indonesian portfolios.
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
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="text-2xl font-bold text-black">Ready to get started?</h2>
          <p className="mt-2 text-sm text-black/50">Contact our team to learn more.</p>
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">
            Get in touch
          </Link>
        </div>
      </section>
    </div>
  );
}
