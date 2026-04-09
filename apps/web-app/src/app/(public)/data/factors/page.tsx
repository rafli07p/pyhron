import Link from 'next/link';

export const metadata = { title: 'Factor Analysis' };

const features = [
  { title: 'Momentum', desc: 'Price and earnings momentum signals calibrated to IDX liquidity conditions and market microstructure.' },
  { title: 'Value', desc: 'Book-to-market, earnings yield, and composite value scores adjusted for Indonesian accounting standards.' },
  { title: 'Quality', desc: 'ROE stability, accruals, and balance sheet health metrics for identifying high-quality Indonesian companies.' },
  { title: 'Size', desc: 'Market-cap-based factor exposures with small-cap premium analysis specific to IDX dynamics.' },
  { title: 'Volatility', desc: 'Low-volatility and minimum-variance factor portfolios optimised for the Indonesian equity universe.' },
];

export default function FactorsPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Factor Analysis</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Systematic factor exposures built for the Indonesian equity market. Research, decompose, and harvest factor premia with institutional rigour.
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
