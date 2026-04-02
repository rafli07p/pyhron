import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import { Star, BarChart3 } from 'lucide-react';
import Link from 'next/link';

export function generateMetadata({ params }: { params: { symbol: string } }) {
  return { title: `${params.symbol} — Markets` };
}

function ChartPlaceholder() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          {['1m', '5m', '15m', '1H', '4H', '1D', '1W'].map((tf) => (
            <button
              key={tf}
              className="rounded px-2 py-0.5 text-xs text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
            >
              {tf}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex h-80 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
          Candlestick chart loads with lightweight-charts
        </div>
      </CardContent>
    </Card>
  );
}

function Fundamentals({ symbol }: { symbol: string }) {
  const data = {
    marketCap: 'IDR 1.200T',
    pe: '18.5x',
    pb: '4.2x',
    roe: '21.3%',
    divYield: '2.8%',
    beta: '0.92',
    high52: '10.250',
    low52: '7.800',
    avgVol: '52.3M',
    freeFloat: '42.3%',
    sector: 'Financials',
    board: 'Regular',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fundamentals</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="space-y-2 text-sm">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <dt className="text-[var(--text-tertiary)]">{key.replace(/([A-Z])/g, ' $1').replace(/^./, (s) => s.toUpperCase())}</dt>
              <dd className="tabular-nums font-medium text-[var(--text-primary)]">{value}</dd>
            </div>
          ))}
          <div className="flex justify-between">
            <dt className="text-[var(--text-tertiary)]">Settlement</dt>
            <dd className="font-medium text-[var(--text-primary)]">T+2</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function OrderBook() {
  const asks = [
    { price: 10000, volume: 12300 },
    { price: 9975, volume: 45600 },
    { price: 9950, volume: 23100 },
  ];
  const bids = [
    { price: 9875, volume: 67800 },
    { price: 9850, volume: 34200 },
    { price: 9825, volume: 19500 },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Order Book (L5)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1 text-xs">
          <div className="grid grid-cols-2 text-[var(--text-tertiary)]">
            <span>Price</span><span className="text-right">Volume</span>
          </div>
          {asks.reverse().map((a) => (
            <div key={a.price} className="grid grid-cols-2 text-[var(--negative)]">
              <span className="tabular-nums">{a.price.toLocaleString('id-ID')}</span>
              <span className="tabular-nums text-right">{a.volume.toLocaleString('id-ID')}</span>
            </div>
          ))}
          <div className="border-y border-[var(--border-default)] py-1 text-center text-xs text-[var(--text-tertiary)]">
            Spread: 25
          </div>
          {bids.map((b) => (
            <div key={b.price} className="grid grid-cols-2 text-[var(--positive)]">
              <span className="tabular-nums">{b.price.toLocaleString('id-ID')}</span>
              <span className="tabular-nums text-right">{b.volume.toLocaleString('id-ID')}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function InstrumentPage({ params }: { params: { symbol: string } }) {
  const { symbol } = params;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${symbol} — Bank Central Asia Tbk`}
        description="IDR 9.875 · +125 (+1.28%) · Vol: 45.2M · MCap: IDR 1.200T"
        actions={
          <div className="flex gap-2">
            <Button variant="ghost" size="sm">
              <Star className="mr-1 h-3.5 w-3.5" /> Watchlist
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/markets/${symbol}/analysis`}>
                <BarChart3 className="mr-1 h-3.5 w-3.5" /> Analysis
              </Link>
            </Button>
            <Button size="sm" asChild>
              <Link href={`/portfolio/orders/new?symbol=${symbol}`}>New Order</Link>
            </Button>
          </div>
        }
      />

      <ChartPlaceholder />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Fundamentals symbol={symbol} />
        <OrderBook />
        <Card>
          <CardHeader>
            <CardTitle>Recent Trades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-xs">
              <div className="grid grid-cols-4 text-[var(--text-tertiary)]">
                <span>Time</span><span>Price</span><span>Vol</span><span>Side</span>
              </div>
              {[
                { time: '14:32:05', price: 9875, vol: 500, side: 'Buy' },
                { time: '14:32:04', price: 9850, vol: 200, side: 'Sell' },
                { time: '14:32:01', price: 9875, vol: 1000, side: 'Buy' },
                { time: '14:31:58', price: 9850, vol: 300, side: 'Sell' },
                { time: '14:31:55', price: 9875, vol: 800, side: 'Buy' },
              ].map((t, i) => (
                <div key={i} className="grid grid-cols-4 tabular-nums">
                  <span className="text-[var(--text-tertiary)]">{t.time}</span>
                  <span className="text-[var(--text-primary)]">{t.price.toLocaleString('id-ID')}</span>
                  <span className="text-[var(--text-secondary)]">{t.vol}</span>
                  <Badge variant={t.side === 'Buy' ? 'positive' : 'negative'} className="w-fit text-[10px]">{t.side}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
