import Link from 'next/link';

export const metadata = { title: 'Machine Learning Research' };

const features = [
  { title: 'Ensemble Models', desc: 'Gradient boosting, random forests, and stacking approaches for equity return prediction on IDX data.' },
  { title: 'Deep Learning for Markets', desc: 'LSTM, transformer, and attention-based architectures applied to Indonesian market time series.' },
  { title: 'Feature Engineering', desc: 'Automated feature selection, alternative data integration, and signal extraction for alpha generation.' },
];

export default function MlResearchPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Machine Learning Research</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">Ensemble models, deep learning architectures, and ML-driven signal generation for Indonesian markets.</p>
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
