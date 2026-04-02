'use client';

import { use, useState, useEffect, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { Input } from '@/design-system/primitives/Input';
import { CandlestickChart, CandlestickChartSkeleton, type OHLCV } from '@/design-system/charts/CandlestickChart';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Skeleton } from '@/design-system/primitives/Skeleton';
import { IDX } from '@/constants/idx';
import { formatIDR, formatNumber, formatVolume } from '@/lib/format';
import { Star, BarChart3 } from 'lucide-react';
import Link from 'next/link';

interface Instrument {
  symbol: string; name: string; sector: string; last_price: number;
  prev_close: number; market_cap: number; lot_size: number; board: string;
  pe?: number; pb?: number; roe?: number; div_yield?: number; beta?: number;
  high_52w?: number; low_52w?: number; avg_volume?: number; free_float?: number;
}

interface OHLCVRaw { timestamp: string; open: number; high: number; low: number; close: number; volume: number; }

const TIMEFRAMES = ['1m', '5m', '15m', '1H', '1D'] as const;

// -- Order Entry Form --------------------------------------------------------

function OrderEntryForm({ instrument }: { instrument: Instrument }) {
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [price, setPrice] = useState(instrument.last_price);
  const [lots, setLots] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const tick = IDX.getTickSize(price);
  const priceValid = price > 0 && price % tick === 0;
  const lotsValid = lots > 0 && Number.isInteger(lots);
  const quantity = lots * 100;
  const cost = IDX.estimateCost(side, price, quantity);

  async function handleSubmit() {
    setSubmitting(true);
    setMessage(null);
    try {
      const res = await fetch('/v1/trading/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: instrument.symbol, side, type: 'limit', price, quantity }),
      });
      if (!res.ok) throw new Error(await res.text());
      setMessage({ type: 'success', text: `Order placed: ${side.toUpperCase()} ${lots} lot @ ${formatIDR(price)}` });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Order failed' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Order Entry</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-1">
          <button onClick={() => setSide('buy')}
            className={`rounded-md py-1.5 text-xs font-semibold transition-colors ${side === 'buy' ? 'bg-[var(--positive)] text-white' : 'bg-[var(--surface-3)] text-[var(--text-secondary)]'}`}>Buy</button>
          <button onClick={() => setSide('sell')}
            className={`rounded-md py-1.5 text-xs font-semibold transition-colors ${side === 'sell' ? 'bg-[var(--negative)] text-white' : 'bg-[var(--surface-3)] text-[var(--text-secondary)]'}`}>Sell</button>
        </div>
        <p className="text-[10px] text-[var(--text-tertiary)]">Type: Limit</p>
        <Input label="Price (IDR)" type="number" value={price} min={tick} step={tick}
          onChange={(e) => setPrice(Number(e.target.value))}
          error={price > 0 && !priceValid ? `Must be multiple of ${tick}` : undefined} />
        <p className="text-[10px] text-[var(--text-tertiary)]">Tick: &plusmn;{tick}</p>
        <Input label="Lots" type="number" value={lots} min={1} step={1}
          onChange={(e) => setLots(Math.floor(Number(e.target.value)))}
          error={lots > 0 && !lotsValid ? 'Must be a positive integer' : undefined} />
        <p className="text-[10px] text-[var(--text-tertiary)]">= {formatNumber(quantity)} shares</p>
        <dl className="space-y-1 text-xs">
          <div className="flex justify-between"><dt className="text-[var(--text-tertiary)]">Est. Value</dt>
            <dd className="tabular-nums font-medium">{formatIDR(cost.value)}</dd></div>
          <div className="flex justify-between"><dt className="text-[var(--text-tertiary)]">Est. Commission</dt>
            <dd className="tabular-nums font-medium">{formatIDR(cost.commission)}</dd></div>
        </dl>
        <Button className="w-full" disabled={!priceValid || !lotsValid || submitting} loading={submitting}
          onClick={handleSubmit}>{submitting ? 'Placing...' : 'Place Order'}</Button>
        <Badge variant="warning" className="w-full justify-center">Paper Trading</Badge>
        {message && <p className={`text-xs text-center ${message.type === 'success' ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>{message.text}</p>}
      </CardContent>
    </Card>
  );
}

// -- Fundamentals Panel ------------------------------------------------------

function Fundamentals({ inst }: { inst: Instrument }) {
  const rows: [string, string][] = [
    ['Market Cap', `IDR ${inst.market_cap.toFixed(0)}T`],
    ['P/E', inst.pe ? `${inst.pe.toFixed(1)}x` : '-'],
    ['P/B', inst.pb ? `${inst.pb.toFixed(1)}x` : '-'],
    ['ROE', inst.roe ? `${inst.roe.toFixed(1)}%` : '-'],
    ['Div Yield', inst.div_yield ? `${inst.div_yield.toFixed(1)}%` : '-'],
    ['Beta', inst.beta ? inst.beta.toFixed(2) : '-'],
    ['52W High', inst.high_52w ? formatIDR(inst.high_52w) : '-'],
    ['52W Low', inst.low_52w ? formatIDR(inst.low_52w) : '-'],
    ['Avg Vol', inst.avg_volume ? formatVolume(inst.avg_volume) : '-'],
    ['Free Float', inst.free_float ? `${inst.free_float.toFixed(1)}%` : '-'],
    ['Sector', inst.sector],
    ['Board', inst.board],
    ['Settlement', IDX.SETTLEMENT],
  ];
  return (
    <Card>
      <CardHeader><CardTitle>Fundamentals</CardTitle></CardHeader>
      <CardContent>
        <dl className="space-y-2 text-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <dt className="text-[var(--text-tertiary)]">{k}</dt>
              <dd className="tabular-nums font-medium text-[var(--text-primary)]">{v}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

// -- Order Book Panel --------------------------------------------------------

const OB_NOISE = [0.42, 0.78, 0.15, 0.63, 0.91, 0.37, 0.55, 0.82, 0.24, 0.69];

function OrderBookPanel({ lastPrice }: { lastPrice: number }) {
  const tick = IDX.getTickSize(lastPrice);
  const { asks, bids, maxVol } = useMemo(() => {
    const a = Array.from({ length: 5 }, (_, i) => ({
      price: lastPrice + (5 - i) * tick,
      volume: Math.round(10_000 + (OB_NOISE[i] ?? 0.5) * 70_000),
    }));
    const b = Array.from({ length: 5 }, (_, i) => ({
      price: lastPrice - (i + 1) * tick,
      volume: Math.round(10_000 + (OB_NOISE[5 + i] ?? 0.5) * 70_000),
    }));
    const mx = Math.max(...a.map((x) => x.volume), ...b.map((x) => x.volume));
    return { asks: a, bids: b, maxVol: mx };
  }, [lastPrice, tick]);
  const spread = (asks[asks.length - 1]?.price ?? 0) - (bids[0]?.price ?? 0);

  return (
    <Card>
      <CardHeader><CardTitle>Order Book (L5)</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-1 text-xs">
          <div className="grid grid-cols-2 text-[var(--text-tertiary)]"><span>Price</span><span className="text-right">Volume</span></div>
          {asks.map((a) => (
            <div key={a.price} className="relative grid grid-cols-2 text-[var(--negative)]">
              <div className="absolute inset-0 bg-[var(--negative)] opacity-10 rounded-sm" style={{ width: `${(a.volume / maxVol) * 100}%`, marginLeft: 'auto' }} />
              <span className="relative tabular-nums">{a.price.toLocaleString('id-ID')}</span>
              <span className="relative tabular-nums text-right">{a.volume.toLocaleString('id-ID')}</span>
            </div>
          ))}
          <div className="border-y border-[var(--border-default)] py-1 text-center text-[var(--text-tertiary)]">Spread: {spread.toLocaleString('id-ID')}</div>
          {bids.map((b) => (
            <div key={b.price} className="relative grid grid-cols-2 text-[var(--positive)]">
              <div className="absolute inset-0 bg-[var(--positive)] opacity-10 rounded-sm" style={{ width: `${(b.volume / maxVol) * 100}%` }} />
              <span className="relative tabular-nums">{b.price.toLocaleString('id-ID')}</span>
              <span className="relative tabular-nums text-right">{b.volume.toLocaleString('id-ID')}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// -- Recent Trades -----------------------------------------------------------

const TRADE_NOISE = [
  { offset: 1.2, volume: 450 }, { offset: 0.4, volume: 1200 }, { offset: 2.1, volume: 800 },
  { offset: 0.8, volume: 350 }, { offset: 1.7, volume: 1600 }, { offset: 0.3, volume: 920 },
  { offset: 2.5, volume: 580 }, { offset: 1.1, volume: 1400 }, { offset: 0.6, volume: 700 },
  { offset: 1.9, volume: 1100 },
];

function RecentTrades({ lastPrice }: { lastPrice: number }) {
  const tick = IDX.getTickSize(lastPrice);
  const trades = useMemo(() => {
    const now = new Date();
    return Array.from({ length: 10 }, (_, i) => {
      const isBuy = i % 2 === 0;
      const noise = TRADE_NOISE[i] ?? { offset: 1, volume: 500 };
      const offset = Math.floor(noise.offset) * tick * (isBuy ? 0 : -1);
      const t = new Date(now.getTime() - i * 3200);
      return {
        time: t.toLocaleTimeString('id-ID', { timeZone: 'Asia/Jakarta', hour12: false }),
        price: lastPrice + offset,
        volume: Math.round(100 + noise.volume),
        side: isBuy ? 'Buy' as const : 'Sell' as const,
      };
    });
  }, [lastPrice, tick]);

  return (
    <Card>
      <CardHeader><CardTitle>Recent Trades</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-1 text-xs">
          <div className="grid grid-cols-4 text-[var(--text-tertiary)]"><span>Time</span><span>Price</span><span>Vol</span><span>Side</span></div>
          {trades.map((t, i) => (
            <div key={i} className="grid grid-cols-4 tabular-nums">
              <span className="text-[var(--text-tertiary)]">{t.time}</span>
              <span className="text-[var(--text-primary)]">{t.price.toLocaleString('id-ID')}</span>
              <span className="text-[var(--text-secondary)]">{t.volume.toLocaleString('id-ID')}</span>
              <Badge variant={t.side === 'Buy' ? 'positive' : 'negative'} className="w-fit text-[10px]">{t.side}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// -- Loading Skeleton --------------------------------------------------------

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="mb-6"><Skeleton className="h-7 w-64" /><Skeleton className="mt-2 h-4 w-96" /></div>
      <CandlestickChartSkeleton height={400} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {[1, 2, 3].map((n) => (<Card key={n} className="p-4"><Skeleton className="h-4 w-24 mb-3" /><div className="space-y-2">{Array.from({ length: 6 }, (_, j) => <Skeleton key={j} className="h-3 w-full" />)}</div></Card>))}
      </div>
    </div>
  );
}

// -- Main Page ---------------------------------------------------------------

export default function InstrumentPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = use(params);
  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [ohlcv, setOhlcv] = useState<OHLCV[]>([]);
  const [timeframe, setTimeframe] = useState<string>('1D');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetch(`/v1/market/instruments/${symbol}`).then((r) => { if (!r.ok) throw new Error('Instrument not found'); return r.json(); }),
      fetch(`/v1/market/ohlcv/${symbol}`).then((r) => { if (!r.ok) throw new Error('OHLCV data unavailable'); return r.json(); }),
    ])
      .then(([instData, ohlcvData]) => {
        if (cancelled) return;
        setInstrument(instData.data ?? instData);
        const bars: OHLCVRaw[] = ohlcvData.data ?? ohlcvData;
        setOhlcv(bars.map((b) => ({
          timestamp: new Date(b.timestamp).getTime() / 1000,
          open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume,
        })));
        setError(null);
      })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [symbol]);

  if (loading) return <PageSkeleton />;

  if (error || !instrument) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Card className="p-8 text-center">
          <p className="text-sm text-[var(--negative)]">{error ?? 'Failed to load instrument'}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => window.location.reload()}>Retry</Button>
        </Card>
      </div>
    );
  }

  const change = instrument.last_price - instrument.prev_close;
  const changePct = (change / instrument.prev_close) * 100;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${symbol} — ${instrument.name}`}
        description={`${formatIDR(instrument.last_price)} · ${change >= 0 ? '+' : ''}${formatNumber(change)} (${change >= 0 ? '+' : ''}${changePct.toFixed(2)}%) · MCap: IDR ${instrument.market_cap.toFixed(0)}T`}
        actions={
          <div className="flex gap-2">
            <Button variant="ghost" size="sm"><Star className="mr-1 h-3.5 w-3.5" /> Watchlist</Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/markets/${symbol}/analysis`}><BarChart3 className="mr-1 h-3.5 w-3.5" /> Analysis</Link>
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            {TIMEFRAMES.map((tf) => (
              <button key={tf} onClick={() => setTimeframe(tf)}
                className={`rounded px-2 py-0.5 text-xs transition-colors ${tf === timeframe ? 'bg-[var(--accent-500)] text-white' : 'text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]'}`}>{tf}</button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <CandlestickChart data={ohlcv} volume height={400} timeframe={timeframe} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <OrderEntryForm instrument={instrument} />
        <Fundamentals inst={instrument} />
        <OrderBookPanel lastPrice={instrument.last_price} />
        <RecentTrades lastPrice={instrument.last_price} />
      </div>

      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
