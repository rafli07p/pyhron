import Link from 'next/link';

export const metadata = { title: 'Market Cap Indexes' };

const features = [
  { title: 'IHSG Composite', desc: 'The Jakarta Composite Index — the broadest measure of Indonesian equity market performance.' },
  { title: 'LQ45', desc: 'The 45 most liquid stocks on the IDX, rebalanced semi-annually based on trading value and frequency.' },
  { title: 'IDX30', desc: 'A concentrated index of the 30 largest and most liquid IDX constituents for benchmark-aware strategies.' },
  { title: 'Small / Mid / Large Cap', desc: 'Market-cap-tiered indexes for size-based allocation, factor research, and performance attribution.' },
];

export default function MarketCapIndexesPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Market Cap Indexes</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Capitalisation-weighted benchmarks spanning the full IDX universe. From the broad IHSG composite to focused large-cap and small-cap indexes.
          </p>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
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
