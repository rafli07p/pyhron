import Link from 'next/link';

export const metadata = { title: 'Market Data' };

const stats = [
  { label: 'Instruments', value: '800+' },
  { label: 'Delivery', value: 'Real-time' },
  { label: 'History', value: '10+ years' },
];

const features = [
  { title: 'OHLCV Data', desc: 'Daily and intraday open, high, low, close, and volume for all IDX-listed instruments.' },
  { title: 'Tick-Level Data', desc: 'Granular trade-by-trade and order book snapshots for microstructure research.' },
  { title: 'Corporate Actions', desc: 'Dividends, stock splits, rights issues, and other events with adjustment factors.' },
  { title: 'Index Data', desc: 'Constituent weights, rebalance history, and calculated values for all major IDX indexes.' },
];

export default function MarketDataPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">Market Data</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">
            Real-time and historical market data covering the full breadth of instruments traded on the Indonesia Stock Exchange.
          </p>
        </div>
      </section>

      <section className="border-b border-black/[0.06] py-12">
        <div className="mx-auto flex max-w-6xl justify-center gap-16 px-6">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-2xl font-bold text-black">{s.value}</p>
              <p className="mt-1 text-sm text-black/50">{s.label}</p>
            </div>
          ))}
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
          <p className="mt-2 text-sm text-black/50">See our market data platform in action.</p>
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">
            Request a demo
          </Link>
        </div>
      </section>
    </div>
  );
}
