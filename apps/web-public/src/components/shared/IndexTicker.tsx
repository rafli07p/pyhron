'use client';

import { useMarketOverview } from '@/lib/hooks/use-market';
import { formatPct, pctColor } from '@/lib/utils/format';

const FALLBACK_TICKERS = [
  { symbol: 'IHSG', price: 7245.32, change_pct: 0.59 },
  { symbol: 'BBCA', price: 9875, change_pct: 1.25 },
  { symbol: 'BBRI', price: 5525, change_pct: -0.45 },
  { symbol: 'TLKM', price: 3840, change_pct: 0.79 },
  { symbol: 'ASII', price: 6925, change_pct: -1.12 },
  { symbol: 'BMRI', price: 6975, change_pct: 0.87 },
  { symbol: 'UNVR', price: 3800, change_pct: -2.31 },
  { symbol: 'BBNI', price: 4850, change_pct: 1.46 },
  { symbol: 'BRIS', price: 2560, change_pct: 2.40 },
];

function TickerItem({ symbol, price, change_pct }: { symbol: string; price: number; change_pct: number }) {
  return (
    <div className="flex items-center gap-3 px-4 whitespace-nowrap">
      <span className="text-sm font-medium font-mono text-text-primary">{symbol}</span>
      <span className="text-sm font-mono text-text-secondary">
        {price.toLocaleString('id-ID')}
      </span>
      <span className={`text-sm font-mono ${pctColor(change_pct)}`}>
        {formatPct(change_pct)}
      </span>
    </div>
  );
}

export function IndexTicker() {
  const { data } = useMarketOverview();
  const tickers = FALLBACK_TICKERS;

  const tickerContent = [...tickers, ...tickers];

  return (
    <div
      className="h-12 overflow-hidden border-y border-border bg-bg-secondary group"
      aria-label="Market ticker"
    >
      <div
        className="flex h-full items-center animate-ticker-scroll group-hover:[animation-play-state:paused]"
        style={{ '--ticker-duration': `${tickers.length * 4}s` } as React.CSSProperties}
      >
        {tickerContent.map((t, i) => (
          <TickerItem key={`${t.symbol}-${i}`} {...t} />
        ))}
      </div>
    </div>
  );
}
