import Link from 'next/link';

export const metadata = { title: 'Indonesian Equities' };

const features = [
  { title: 'LQ45 Coverage', desc: 'Complete data for the 45 most liquid stocks on the IDX, including intraday and end-of-day snapshots.' },
  { title: 'IDX80 & Beyond', desc: 'Extended coverage across IDX80, IDX30, and the full listed universe of 800+ equities.' },
  { title: 'Full Universe', desc: 'Every listed equity on the Indonesia Stock Exchange, from mega-cap banks to micro-cap explorers.' },
  { title: 'T+2 Settlement Aware', desc: 'Trade date vs. settlement date handling built in, ensuring accurate P&L and position tracking.' },
];

export default function EquitiesPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Indonesian Equities</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Comprehensive equity data for the Indonesia Stock Exchange. From blue-chip LQ45 names to the full listed universe.
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
