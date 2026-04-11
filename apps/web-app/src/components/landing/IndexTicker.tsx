'use client';

import { useState } from 'react';
import { ArrowUp, ArrowDown, Pause, Play } from 'lucide-react';

/**
 * Horizontal auto-scrolling ticker for Indonesia's top stock-market indices.
 *
 * Renders a single row of index chips (IHSG, LQ45, IDX30, …) and duplicates
 * the list so the CSS keyframe can translate the inner flex-track from 0% to
 * -50% in a seamless loop. The user can pause/resume via the button on the
 * right; pausing applies `animation-play-state: paused` to the track.
 */

interface IndexItem {
  symbol: string;
  name: string;
  change: number;
  currency: 'IDR';
  value: number;
  asOf: string;
}

// Snapshot values (2026-04-10). Not real-time — these are representative
// numbers to power the visual ticker; wire up a live feed later.
const INDICES: IndexItem[] = [
  { symbol: 'IHSG',        name: 'IHSG',        change: 0.67, currency: 'IDR', value: 7285.42,  asOf: 'Apr 10' },
  { symbol: 'LQ45',        name: 'LQ45',        change: 0.08, currency: 'IDR', value:  923.18,  asOf: 'Apr 10' },
  { symbol: 'IDX30',       name: 'IDX30',       change: -0.21, currency: 'IDR', value:  481.66, asOf: 'Apr 10' },
  { symbol: 'IDX80',       name: 'IDX80',       change: 0.43, currency: 'IDR', value:  148.92,  asOf: 'Apr 10' },
  { symbol: 'KOMPAS100',   name: 'KOMPAS100',   change: 0.55, currency: 'IDR', value: 1212.30,  asOf: 'Apr 10' },
  { symbol: 'JII',         name: 'JII',         change: -0.12, currency: 'IDR', value:  543.87, asOf: 'Apr 10' },
  { symbol: 'JII70',       name: 'JII70',       change: 0.18, currency: 'IDR', value:  228.44,  asOf: 'Apr 10' },
  { symbol: 'IDXBUMN20',   name: 'IDXBUMN20',   change: 1.24, currency: 'IDR', value:  389.15,  asOf: 'Apr 10' },
  { symbol: 'IDXHIDIV20',  name: 'IDXHIDIV20',  change: 0.32, currency: 'IDR', value:  477.09,  asOf: 'Apr 10' },
  { symbol: 'SRI-KEHATI',  name: 'SRI-KEHATI',  change: 0.21, currency: 'IDR', value:  420.55,  asOf: 'Apr 10' },
];

const valueFormat = new Intl.NumberFormat('id-ID', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function TickerItem({ item }: { item: IndexItem }) {
  const positive = item.change >= 0;
  return (
    <div className="flex shrink-0 items-center gap-3 border-r border-black/10 px-8">
      <div className="flex flex-col gap-0.5">
        <span className="text-[13px] font-semibold text-black">{item.name}</span>
        <span className="text-[11px] font-normal text-black/45">{item.asOf}</span>
      </div>
      <div className="flex flex-col items-start gap-0.5">
        <span
          className={`flex items-center gap-0.5 text-[13px] font-semibold ${
            positive ? 'text-[#16a34a]' : 'text-[#dc2626]'
          }`}
        >
          {positive ? (
            <ArrowUp className="h-3 w-3" strokeWidth={3} />
          ) : (
            <ArrowDown className="h-3 w-3" strokeWidth={3} />
          )}
          {Math.abs(item.change).toFixed(2)}%
        </span>
        <span className="text-[11px] font-normal text-black/55">
          {item.currency} {valueFormat.format(item.value)}
        </span>
      </div>
    </div>
  );
}

export function IndexTicker() {
  const [paused, setPaused] = useState(false);

  return (
    <section className="bg-white py-14">
      <div className="mx-auto max-w-[1200px] px-6 lg:px-8">
        <div className="relative flex items-center overflow-hidden rounded-full border border-black/10 bg-white shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
          {/* Track wrapper — masks the right side so the pause button sits on top. */}
          <div className="relative flex-1 overflow-hidden">
            <div
              className="index-ticker-track flex w-max items-stretch py-4"
              style={{ animationPlayState: paused ? 'paused' : 'running' }}
            >
              {INDICES.map((item) => (
                <TickerItem key={`a-${item.symbol}`} item={item} />
              ))}
              {/* Duplicate the list so the -50% translate produces a seamless loop. */}
              {INDICES.map((item) => (
                <TickerItem key={`b-${item.symbol}`} item={item} />
              ))}
            </div>
            {/* Left/right fade masks */}
            <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-white to-transparent" />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-white to-transparent" />
          </div>

          {/* Pause / resume */}
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            aria-label={paused ? 'Resume ticker' : 'Pause ticker'}
            className="mr-3 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-black/10 text-black transition-colors hover:bg-black/[0.04]"
          >
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes index-ticker-scroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
        .index-ticker-track {
          animation: index-ticker-scroll 40s linear infinite;
          will-change: transform;
        }
        @media (prefers-reduced-motion: reduce) {
          .index-ticker-track { animation: none; }
        }
      `}</style>
    </section>
  );
}
