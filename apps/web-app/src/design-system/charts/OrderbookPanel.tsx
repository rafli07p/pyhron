import { cn } from '@/lib/utils';

export interface OrderbookRow {
  price: number;
  volume: number;
  total: number;
}

interface OrderbookPanelProps {
  symbol: string;
  bids: OrderbookRow[];
  asks: OrderbookRow[];
  maxLevels?: number;
  className?: string;
}

const ROW_HEIGHT = 24;

function fmtIDR(n: number): string {
  return n.toLocaleString('id-ID');
}

function fmtInt(n: number): string {
  return n.toLocaleString('en-US');
}

export function OrderbookPanel({
  symbol,
  bids,
  asks,
  maxLevels = 10,
  className,
}: OrderbookPanelProps) {
  const askRows = asks.slice(0, maxLevels);
  const bidRows = bids.slice(0, maxLevels);

  // Asks are displayed top-down with lowest (best) ask closest to spread row
  const askDisplay = [...askRows].reverse();

  const bestAsk = askRows[0]?.price;
  const bestBid = bidRows[0]?.price;
  const spread =
    bestAsk !== undefined && bestBid !== undefined ? bestAsk - bestBid : undefined;
  const spreadPct =
    spread !== undefined && bestBid ? (spread / bestBid) * 100 : undefined;

  const maxAskVolume = askRows.reduce((m, r) => Math.max(m, r.volume), 0);
  const maxBidVolume = bidRows.reduce((m, r) => Math.max(m, r.volume), 0);

  return (
    <div
      className={cn('overflow-hidden', className)}
      style={{
        background: 'var(--color-bg-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        fontVariantNumeric: 'tabular-nums',
      }}
      aria-label={`Orderbook for ${symbol}`}
    >
      <div
        className="grid grid-cols-3 text-[11px] font-semibold uppercase tracking-wide"
        style={{
          color: 'var(--color-text-muted)',
          padding: '10px 14px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-bg-card)',
        }}
      >
        <span className="text-left">Price (IDR)</span>
        <span className="text-right">Volume</span>
        <span className="text-right">Total</span>
      </div>

      <div role="rowgroup" aria-label="Asks">
        {askDisplay.map((row) => (
          <OrderbookRowView
            key={`ask-${row.price}`}
            row={row}
            side="ask"
            fillPct={maxAskVolume ? (row.volume / maxAskVolume) * 100 : 0}
          />
        ))}
      </div>

      <div
        className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide"
        style={{
          padding: '8px 14px',
          background: 'var(--color-border-subtle, #F0F4F8)',
          borderTop: '1px solid var(--color-border)',
          borderBottom: '1px solid var(--color-border)',
          color: 'var(--color-text-secondary)',
        }}
      >
        <span>Spread</span>
        <span className="tabular-nums" style={{ color: 'var(--color-text-primary)' }}>
          {spread !== undefined ? fmtIDR(spread) : '—'}
          {spreadPct !== undefined && (
            <span style={{ marginLeft: 8, color: 'var(--color-text-muted)' }}>
              ({spreadPct.toFixed(2)}%)
            </span>
          )}
        </span>
      </div>

      <div role="rowgroup" aria-label="Bids">
        {bidRows.map((row) => (
          <OrderbookRowView
            key={`bid-${row.price}`}
            row={row}
            side="bid"
            fillPct={maxBidVolume ? (row.volume / maxBidVolume) * 100 : 0}
          />
        ))}
      </div>
    </div>
  );
}

function OrderbookRowView({
  row,
  side,
  fillPct,
}: {
  row: OrderbookRow;
  side: 'ask' | 'bid';
  fillPct: number;
}) {
  const isAsk = side === 'ask';
  const priceColor = isAsk ? 'var(--color-negative)' : 'var(--color-positive)';
  const fillBg = isAsk ? 'var(--color-negative-bg)' : 'var(--color-positive-bg)';

  return (
    <div
      className="relative grid grid-cols-3 text-[12px]"
      style={{
        height: ROW_HEIGHT,
        alignItems: 'center',
        padding: '0 14px',
        borderBottom: '1px solid var(--color-border-subtle, #F0F4F8)',
      }}
      role="row"
    >
      <div
        aria-hidden
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          right: 0,
          width: `${fillPct}%`,
          background: fillBg,
          opacity: 0.6,
          pointerEvents: 'none',
        }}
      />
      <span
        className="relative font-mono"
        style={{ color: priceColor, fontWeight: 600 }}
      >
        {fmtIDR(row.price)}
      </span>
      <span className="relative text-right" style={{ color: 'var(--color-text-primary)' }}>
        {fmtInt(row.volume)}
      </span>
      <span className="relative text-right" style={{ color: 'var(--color-text-muted)' }}>
        {fmtInt(row.total)}
      </span>
    </div>
  );
}
