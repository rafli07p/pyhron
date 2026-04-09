import Link from 'next/link';

export const metadata = { title: 'Fundamental Data' };

const features = [
  { title: 'Financial Statements', desc: 'Standardised income statements, balance sheets, and cash flow statements for all IDX-listed companies.' },
  { title: 'Valuation Ratios', desc: 'P/E, P/B, EV/EBITDA, dividend yield, and dozens more — calculated daily with point-in-time accuracy.' },
  { title: 'Earnings Estimates', desc: 'Consensus analyst estimates, revisions tracking, and surprise history for top-coverage stocks.' },
  { title: 'Dividend History', desc: 'Complete dividend payment records including ex-dates, payment dates, and yield calculations.' },
];

export default function FundamentalsPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Fundamental Data</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Deep fundamental coverage of Indonesian equities with point-in-time accuracy to eliminate look-ahead bias in your research.
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
