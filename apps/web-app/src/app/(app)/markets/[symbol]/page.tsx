'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { CandlestickChart, type OHLCV } from '@/design-system/charts/CandlestickChart';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';
import { IDX } from '@/constants/idx';
import { getInstrumentDetail, generateOHLCV } from '@/mocks/terminal-data';
import { formatIDR, formatNumber, formatVolume } from '@/lib/format';

const TABS = ['Overview', 'Financials', 'Technical', 'Peers'] as const;
const TIME_RANGES = ['1M', '3M', '6M', '1Y', 'ALL'] as const;

function Label({ children }: { children: React.ReactNode }) {
  return <span className="text-[10px] uppercase text-white/30">{children}</span>;
}
function Val({ children }: { children: React.ReactNode }) {
  return <span className="text-sm font-mono text-white">{children}</span>;
}

export default function InstrumentPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = React.use(params);
  const inst = getInstrumentDetail(symbol);

  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview');
  const [timeRange, setTimeRange] = useState('1Y');
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [lots, setLots] = useState(1);
  const [price, setPrice] = useState(inst.currentPrice);
  const [errors, setErrors] = useState<{ lots?: string; price?: string }>({});

  const ohlcvRaw = generateOHLCV(inst.currentPrice, 120);
  const chartData: OHLCV[] = ohlcvRaw.map((d) => ({
    timestamp: Math.floor(new Date(d.date).getTime() / 1000),
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
    volume: d.volume,
  }));

  const positive = inst.changePct >= 0;
  const tick = inst.tickSize;

  function validate() {
    const e: { lots?: string; price?: string } = {};
    if (!Number.isInteger(lots) || lots <= 0) e.lots = 'Must be a positive integer';
    if (price <= 0 || price % tick !== 0) e.price = `Must be a positive multiple of ${tick}`;
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handlePlaceOrder() {
    if (!validate()) return;
    // Paper trading -- no actual submission
  }

  const qty = lots * IDX.LOT_SIZE;
  const cost = IDX.estimateCost(side, price, qty);

  const mcapT = (inst.marketCap / 1_000_000_000_000).toFixed(0);

  return (
    <div className="p-4 space-y-3">
      {/* Header */}
      <div>
        <Link href="/markets" className="text-xs text-white/30 hover:text-white/50 transition-colors">
          &larr; Markets
        </Link>
        <h1 className="text-lg font-medium text-white mt-1">
          {inst.symbol} <span className="text-white/40 font-normal">&middot;</span>{' '}
          <span className="text-white/60 font-normal text-sm">{inst.name}</span>{' '}
          <span className="text-white/40 font-normal text-sm">&middot; ● {inst.board} Board</span>
        </h1>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[#1e1e22] pb-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              t === tab ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' ? (
        <>
          {/* 4 info panels */}
          <div className="grid grid-cols-4 gap-3">
            {/* Price panel */}
            <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22] space-y-2">
              <Label>Price</Label>
              <div className="font-mono text-lg text-white">{formatIDR(inst.currentPrice)}</div>
              <div className={`font-mono text-xs ${positive ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                {positive ? '+' : ''}{formatNumber(inst.change)} ({positive ? '+' : ''}{inst.changePct.toFixed(2)}%)
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-1">
                <div><Label>Open</Label><div><Val>{formatNumber(inst.open)}</Val></div></div>
                <div><Label>High</Label><div><Val>{formatNumber(inst.dayHigh)}</Val></div></div>
                <div><Label>Low</Label><div><Val>{formatNumber(inst.dayLow)}</Val></div></div>
                <div><Label>Volume</Label><div><Val>{formatVolume(inst.volume)}</Val></div></div>
              </div>
            </div>

            {/* Performance panel */}
            <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22] space-y-2">
              <Label>Performance</Label>
              <div className="space-y-1 pt-1">
                {[
                  ['1W', '+1.4%'], ['1M', '+3.2%'], ['3M', '+5.7%'],
                  ['YTD', '+8.2%'], ['1Y', '+12.1%'],
                ].map(([period, val]) => (
                  <div key={period} className="flex justify-between">
                    <Label>{period}</Label>
                    <Val>{val}</Val>
                  </div>
                ))}
              </div>
            </div>

            {/* Fundamentals panel */}
            <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22] space-y-2">
              <Label>Fundamentals</Label>
              <div className="space-y-1 pt-1">
                {[
                  ['P/E', `${inst.peRatio.toFixed(1)}x`],
                  ['P/B', `${inst.pbRatio.toFixed(1)}x`],
                  ['Div Yield', `${inst.divYield.toFixed(1)}%`],
                  ['EPS', `${(inst.currentPrice / inst.peRatio).toFixed(0)}`],
                  ['ROE', `${inst.roe.toFixed(1)}%`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <Label>{k}</Label>
                    <Val>{v}</Val>
                  </div>
                ))}
              </div>
            </div>

            {/* Trading panel */}
            <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22] space-y-2">
              <Label>Trading</Label>
              <div className="space-y-1 pt-1">
                {[
                  ['52W High', formatNumber(inst.high52w)],
                  ['52W Low', formatNumber(inst.low52w)],
                  ['Avg Vol', formatVolume(inst.avgVolume30d)],
                  ['MCap', `IDR ${mcapT}T`],
                  ['Board', inst.board],
                  ['Lot Size', `${inst.lotSize}`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <Label>{k}</Label>
                    <Val>{v}</Val>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Chart + Order Entry */}
          <div className="grid grid-cols-3 gap-3">
            {/* Price Chart */}
            <div className="col-span-2">
              <CandlestickChart data={chartData} volume height={250} timeframe="1D" />
              <div className="flex items-center gap-1 mt-2">
                {TIME_RANGES.map((tr) => (
                  <button
                    key={tr}
                    onClick={() => setTimeRange(tr)}
                    className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                      tr === timeRange ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/50'
                    }`}
                  >
                    {tr}
                  </button>
                ))}
              </div>
            </div>

            {/* Order Entry */}
            <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22] space-y-3">
              <div className="flex items-center justify-between">
                <Label>Order Entry</Label>
                <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[9px] font-medium text-amber-400">
                  Paper Trading
                </span>
              </div>

              {/* BUY/SELL toggle */}
              <div className="grid grid-cols-2 gap-1">
                <button
                  onClick={() => setSide('buy')}
                  className={`rounded py-1.5 text-xs font-semibold transition-colors ${
                    side === 'buy' ? 'bg-[#2563eb] text-white' : 'bg-white/5 text-white/40'
                  }`}
                >
                  BUY
                </button>
                <button
                  onClick={() => setSide('sell')}
                  className={`rounded py-1.5 text-xs font-semibold transition-colors ${
                    side === 'sell' ? 'bg-[#ef4444] text-white' : 'bg-white/5 text-white/40'
                  }`}
                >
                  SELL
                </button>
              </div>

              {/* Qty */}
              <div>
                <label className="text-[10px] uppercase text-white/30">Qty (lots)</label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={lots}
                  onChange={(e) => setLots(Math.floor(Number(e.target.value)))}
                  className="mt-1 w-full rounded bg-white/5 border border-[#1e1e22] px-2 py-1.5 font-mono text-sm text-white outline-none focus:border-white/20"
                />
                {errors.lots && <p className="text-[10px] text-[#ef4444] mt-0.5">{errors.lots}</p>}
                <p className="text-[10px] text-white/20 mt-0.5">= {formatNumber(qty)} shares</p>
              </div>

              {/* Price */}
              <div>
                <label className="text-[10px] uppercase text-white/30">Price (IDR)</label>
                <input
                  type="number"
                  min={tick}
                  step={tick}
                  value={price}
                  onChange={(e) => setPrice(Number(e.target.value))}
                  className="mt-1 w-full rounded bg-white/5 border border-[#1e1e22] px-2 py-1.5 font-mono text-sm text-white outline-none focus:border-white/20"
                />
                {errors.price && <p className="text-[10px] text-[#ef4444] mt-0.5">{errors.price}</p>}
                <p className="text-[10px] text-white/20 mt-0.5">Tick: &plusmn;{tick}</p>
              </div>

              {/* Cost summary */}
              <div className="space-y-1 border-t border-[#1e1e22] pt-2">
                <div className="flex justify-between text-xs">
                  <span className="text-white/30">Est. Value</span>
                  <span className="font-mono text-white">{formatIDR(cost.value)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-white/30">Commission</span>
                  <span className="font-mono text-white">{formatIDR(cost.commission)}</span>
                </div>
              </div>

              <button
                onClick={handlePlaceOrder}
                className={`w-full rounded py-2 text-xs font-semibold transition-colors ${
                  side === 'buy'
                    ? 'bg-[#2563eb] hover:bg-[#1d4ed8] text-white'
                    : 'bg-[#ef4444] hover:bg-[#dc2626] text-white'
                }`}
              >
                Place Order
              </button>
            </div>
          </div>

          {/* Description */}
          <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22]">
            <Label>Description</Label>
            <p className="text-xs text-white/50 mt-1 leading-relaxed">{inst.description}</p>
          </div>
        </>
      ) : (
        <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22] flex items-center justify-center h-48">
          <span className="text-xs text-white/30">{tab} -- coming soon</span>
        </div>
      )}

      <TerminalDisclaimer />
    </div>
  );
}
