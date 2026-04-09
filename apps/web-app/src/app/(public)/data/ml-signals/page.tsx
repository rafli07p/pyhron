import Link from 'next/link';

export const metadata = { title: 'ML-Driven Signals' };

const features = [
  { title: 'Ensemble Models', desc: 'Gradient-boosted trees, neural networks, and linear models combined to produce robust alpha signals for IDX equities.' },
  { title: 'Confidence Scoring', desc: 'Each signal includes a calibrated probability score so you can size positions according to conviction.' },
  { title: 'Factor-Based Predictions', desc: 'ML models trained on Pyhron factor data to forecast cross-sectional returns at daily and weekly horizons.' },
];

export default function MlSignalsPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">ML-Driven Signals</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Machine-learning-powered alpha signals trained on Indonesian market data. Designed for systematic strategies that demand rigorous out-of-sample validation.
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
