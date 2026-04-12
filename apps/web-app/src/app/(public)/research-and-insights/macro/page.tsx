import Link from 'next/link';

export const metadata = { title: 'Macro & Economic Research' };

const features = [
  { title: 'BI Rate Analysis', desc: 'Bank Indonesia monetary policy analysis, rate decision forecasting, and impact assessment on IDX markets.' },
  { title: 'Inflation & Growth', desc: 'CPI decomposition, GDP nowcasting, and leading indicator models for the Indonesian economy.' },
  { title: 'Currency & Capital Flows', desc: 'USD/IDR dynamics, foreign fund flows, and balance-of-payments analysis for portfolio positioning.' },
];

export default function MacroResearchPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <Link href="/research-and-insights" className="text-sm text-[#2563eb] hover:underline">&larr; Back to Research & Insights</Link>
          <h1 className="mt-4 text-3xl font-bold text-black">Macro & Economic Research</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">BI rate analysis, inflation monitoring, and currency dynamics research for Indonesian macro investing.</p>
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
