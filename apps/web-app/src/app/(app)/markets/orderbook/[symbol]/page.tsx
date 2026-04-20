import { PageHeader } from '@/design-system/layout/PageHeader';
import { OrderbookPanel } from '@/design-system/charts/OrderbookPanel';
import { generateOrderbook } from '@/mocks/generators/orderbook';
import { RefreshButton } from './RefreshButton';

export const dynamic = 'force-dynamic';

export default async function OrderbookPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  const upper = symbol.toUpperCase();
  const snapshot = generateOrderbook(upper);

  const updated = new Date(snapshot.timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Asia/Jakarta',
  });

  return (
    <div className="mx-auto w-full max-w-[1440px] p-4 md:p-6">
      <PageHeader
        title={`${upper} Orderbook`}
        description="Level 2 market depth · IDX"
        actions={<RefreshButton />}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[420px_1fr]">
        <OrderbookPanel symbol={upper} bids={snapshot.bids} asks={snapshot.asks} />

        <aside
          className="flex flex-col"
          style={{
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            padding: 16,
          }}
        >
          <span
            className="text-[11px] font-semibold uppercase tracking-wide"
            style={{ color: 'var(--color-text-muted)' }}
          >
            Last updated
          </span>
          <span
            className="tabular-nums"
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              marginTop: 4,
            }}
          >
            {updated} WIB
          </span>
          <p
            className="mt-3 text-xs"
            style={{ color: 'var(--color-text-secondary)', lineHeight: 1.5 }}
          >
            Depth snapshot refreshes every 5 seconds. Prices follow IDX tick-size rules;
            volume is expressed in lots (1 lot = 100 shares).
          </p>
        </aside>
      </div>
    </div>
  );
}
