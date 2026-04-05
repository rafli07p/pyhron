import { PlaceholderLogo } from '@/components/ui/PlaceholderLogo';

const LOGOS = [
  { name: 'IDX', width: 80 },
  { name: 'OJK', width: 70 },
  { name: 'Bloomberg', width: 120 },
  { name: 'Reuters', width: 100 },
  { name: 'yfinance', width: 90 },
  { name: 'Alpaca', width: 90 },
];

export function TrustedBy() {
  return (
    <section className="border-y border-white/[0.04] py-8">
      <div className="mx-auto max-w-6xl px-6">
        <p className="mb-6 text-center text-[9px] uppercase tracking-[0.3em] text-white/15">
          Data &amp; Infrastructure Partners
        </p>
        <div className="flex flex-wrap items-center justify-center gap-12">
          {LOGOS.map((l) => <PlaceholderLogo key={l.name} name={l.name} width={l.width} />)}
        </div>
      </div>
    </section>
  );
}
