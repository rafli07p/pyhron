'use client';

import { useState } from 'react';
import Link from 'next/link';
import { MiniChart } from '@/design-system/charts/MiniChart';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';
import { INDICES, SECTORS, MARKET_BREADTH, generateSparkline } from '@/mocks/terminal-data';

const GAINERS = [
  { symbol: 'BREN', name: 'Barito Renewables', price: 8250, change: 4.8, volume: '125.3M' },
  { symbol: 'BBCA', name: 'Bank Central Asia', price: 9875, change: 2.3, volume: '45.2M' },
  { symbol: 'PANI', name: 'Pantai Indah Kapuk', price: 14250, change: 1.9, volume: '32.1M' },
  { symbol: 'BMRI', name: 'Bank Mandiri', price: 6225, change: 0.8, volume: '34.5M' },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia', price: 4850, change: 0.6, volume: '52.7M' },
  { symbol: 'AMRT', name: 'Sumber Alfaria', price: 2780, change: 0.3, volume: '18.4M' },
];

const LOSERS = [
  { symbol: 'GOTO', name: 'GoTo Gojek Tokopedia', price: 82, change: -3.5, volume: '892.1M' },
  { symbol: 'TLKM', name: 'Telkom Indonesia', price: 3850, change: -1.1, volume: '67.8M' },
  { symbol: 'UNVR', name: 'Unilever Indonesia', price: 4150, change: -0.7, volume: '22.3M' },
  { symbol: 'ASII', name: 'Astra International', price: 4750, change: -0.5, volume: '28.9M' },
  { symbol: 'ICBP', name: 'Indofood CBP', price: 11200, change: -0.4, volume: '15.6M' },
  { symbol: 'INDF', name: 'Indofood Sukses', price: 6850, change: -0.3, volume: '12.8M' },
];

function fmt(n: number) {
  return n.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function MarketsPage() {
  const [tab, setTab] = useState<'gainers' | 'losers'>('gainers');
  const movers = tab === 'gainers' ? GAINERS : LOSERS;
  const total = MARKET_BREADTH.advancing + MARKET_BREADTH.declining + MARKET_BREADTH.unchanged;

  return (
    <div className="p-4 space-y-3">
      <h1 className="text-lg font-medium text-white">Markets</h1>

      {/* Index cards */}
      <div className="grid grid-cols-6 gap-3">
        {INDICES.map((idx) => {
          const positive = idx.changePct >= 0;
          const spark = generateSparkline(20, idx.value, 50);
          return (
            <div key={idx.symbol} className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22]">
              <div className="text-[10px] uppercase text-white/30">{idx.symbol}</div>
              <div className="font-mono text-lg text-white">{fmt(idx.value)}</div>
              <div className="flex items-center justify-between">
                <span className={`font-mono text-xs ${positive ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                  {positive ? '+' : ''}{idx.changePct.toFixed(2)}%
                </span>
                <MiniChart data={spark} width={60} height={20} positive={positive} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Market Breadth */}
      <div className="p-3 rounded-lg bg-[#111113] border border-[#1e1e22]">
        <div className="flex items-center justify-between text-xs text-white/50 mb-2">
          <span>Market Breadth</span>
          <span className="font-mono">
            <span className="text-[#22c55e]">Advancing {MARKET_BREADTH.advancing}</span>
            {' | '}
            <span className="text-[#ef4444]">Declining {MARKET_BREADTH.declining}</span>
            {' | '}
            <span className="text-white/40">Unchanged {MARKET_BREADTH.unchanged}</span>
          </span>
        </div>
        <div className="flex h-2 w-full overflow-hidden rounded-full">
          <div className="bg-[#22c55e]" style={{ width: `${(MARKET_BREADTH.advancing / total) * 100}%` }} />
          <div className="bg-[#ef4444]" style={{ width: `${(MARKET_BREADTH.declining / total) * 100}%` }} />
          <div className="bg-white/20" style={{ width: `${(MARKET_BREADTH.unchanged / total) * 100}%` }} />
        </div>
      </div>

      {/* Sector Heatmap */}
      <div>
        <div className="text-xs text-white/50 mb-2">Sector Heatmap</div>
        <div className="grid grid-cols-3 gap-1">
          {SECTORS.map((s) => {
            const positive = s.change >= 0;
            const mag = Math.min(Math.abs(s.change) / 3, 1);
            const bg = positive
              ? `rgba(34,197,94,${0.08 + mag * 0.22})`
              : `rgba(239,68,68,${0.08 + mag * 0.22})`;
            return (
              <div
                key={s.name}
                className="flex flex-col items-center justify-center rounded-md p-2"
                style={{ minHeight: 50, backgroundColor: bg }}
              >
                <span className="text-xs text-white/70">{s.name}</span>
                <span className={`font-mono text-sm ${positive ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                  {positive ? '+' : ''}{s.change.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Movers */}
      <div>
        <div className="flex items-center gap-1 mb-2">
          <button
            onClick={() => setTab('gainers')}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              tab === 'gainers' ? 'bg-[#22c55e]/20 text-[#22c55e]' : 'text-white/40 hover:text-white/60'
            }`}
          >
            Gainers
          </button>
          <button
            onClick={() => setTab('losers')}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              tab === 'losers' ? 'bg-[#ef4444]/20 text-[#ef4444]' : 'text-white/40 hover:text-white/60'
            }`}
          >
            Losers
          </button>
        </div>
        <div className="rounded-lg bg-[#111113] border border-[#1e1e22] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e1e22]">
                <th className="px-3 py-2 text-left text-[10px] uppercase text-white/30 font-medium">Symbol</th>
                <th className="px-3 py-2 text-left text-[10px] uppercase text-white/30 font-medium">Name</th>
                <th className="px-3 py-2 text-right text-[10px] uppercase text-white/30 font-medium">Price</th>
                <th className="px-3 py-2 text-right text-[10px] uppercase text-white/30 font-medium">Change%</th>
                <th className="px-3 py-2 text-right text-[10px] uppercase text-white/30 font-medium">Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e22]">
              {movers.map((s) => {
                const positive = s.change >= 0;
                return (
                  <tr key={s.symbol} className="hover:bg-white/[0.02]">
                    <td className="px-3 py-2">
                      <Link href={`/markets/${s.symbol}`} className="font-mono text-sm text-white hover:underline">
                        {s.symbol}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-white/50 text-xs">{s.name}</td>
                    <td className="px-3 py-2 text-right font-mono text-white">
                      {s.price.toLocaleString('id-ID')}
                    </td>
                    <td className={`px-3 py-2 text-right font-mono font-medium ${positive ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                      {positive ? '+' : ''}{s.change.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-white/40">{s.volume}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <TerminalDisclaimer />
    </div>
  );
}
