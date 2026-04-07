import Link from 'next/link';
import { Check } from 'lucide-react';

const terminalLines = [
  { type: 'prompt', text: '$ pyhron screen --universe LQ45 --factor momentum --top 10' },
  { type: 'header', text: 'Symbol   Score   Return_1M   Sharpe   Signal' },
  { type: 'line', text: 'BBCA     0.87    +4.2%       1.84     BUY' },
  { type: 'line', text: 'BMRI     0.81    +3.5%       1.62     BUY' },
  { type: 'line', text: 'BBRI     0.78    +2.9%       1.45     BUY' },
  { type: 'line', text: 'TLKM     0.74    +2.8%       1.38     BUY' },
  { type: 'line', text: 'ASII     0.62    +1.2%       0.95     HOLD' },
  { type: 'prompt', text: '$ pyhron risk --portfolio --var 95' },
  { type: 'line', text: 'VaR(95,1d): IDR 45.2M (-1.2%)  Sharpe: 1.84' },
  { type: 'line', text: 'Max DD: -7.3%  Beta(IHSG): 0.92  Alpha: +8.2%' },
];

const bullets = [
  'Real-time tick data with T+2 settlement awareness',
  'IDR-denominated P&L and risk metrics',
  'Lot-size adjusted position sizing (100-share minimum)',
  'Integrated corporate action adjustments',
];

export function PlatformPreview() {
  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid grid-cols-1 items-center gap-16 lg:grid-cols-5">
          {/* Left content */}
          <div className="lg:col-span-2">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#6B7280]">
              The Terminal
            </p>
            <h2 className="mt-4 text-3xl font-normal tracking-tight text-[#1A1A2E] lg:text-4xl">
              Bloomberg-grade analytics, built for Indonesia
            </h2>
            <ul className="mt-8 space-y-4">
              {bullets.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#C9A84C]" strokeWidth={2.5} />
                  <span className="text-sm leading-relaxed text-[#6B7280]">{item}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/register"
              className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-[#0A1628] transition-colors hover:text-[#C9A84C]"
            >
              Request Early Access &rarr;
            </Link>
          </div>

          {/* Right — terminal mockup */}
          <div className="lg:col-span-3">
            <div className="overflow-hidden rounded-lg border border-[#1E3A5F]/20 bg-[#0A1628] shadow-2xl">
              {/* Title bar */}
              <div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
                <div className="h-3 w-3 rounded-full bg-[#ef4444]/60" />
                <div className="h-3 w-3 rounded-full bg-[#eab308]/60" />
                <div className="h-3 w-3 rounded-full bg-[#22c55e]/60" />
                <span className="ml-2 text-[11px] text-white/30">pyhron-terminal</span>
              </div>
              {/* Terminal content */}
              <div className="p-5 font-mono text-xs leading-relaxed">
                {terminalLines.map((line, i) => (
                  <p
                    key={i}
                    className={
                      line.type === 'prompt'
                        ? 'mt-3 text-[#C9A84C] first:mt-0'
                        : line.type === 'header'
                          ? 'mt-1 text-white/40'
                          : 'text-white/70'
                    }
                  >
                    {line.text}
                  </p>
                ))}
                <p className="mt-3 animate-pulse text-[#C9A84C]">$ _</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
