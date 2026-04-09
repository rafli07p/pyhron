import Link from 'next/link';

export const metadata = { title: 'Shariah-Compliant Indexes' };

const features = [
  { title: 'JII (Jakarta Islamic Index)', desc: 'The 30 most liquid shariah-compliant stocks on the IDX, screened by OJK and DSN-MUI criteria.' },
  { title: 'ISSI (Indonesia Sharia Stock Index)', desc: 'Full universe of shariah-compliant equities listed on the Indonesia Stock Exchange.' },
  { title: 'Islamic Finance Benchmarks', desc: 'Composite indexes tracking the performance of Islamic finance instruments across asset classes.' },
];

export default function ShariahIndexesPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Shariah-Compliant Indexes</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">JII, ISSI, and Islamic finance indexes for shariah-compliant investment strategies in Indonesia.</p>
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
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">Get in touch</Link>
        </div>
      </section>
    </div>
  );
}
