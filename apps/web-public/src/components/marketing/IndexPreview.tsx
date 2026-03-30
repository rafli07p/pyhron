'use client';

import { useState } from 'react';
import { StockChart } from '@/components/charts/StockChart';
import { mockIndexData, mockIndexPerformance } from '@/lib/mock/data/indices';
import { formatPct, pctColor } from '@/lib/utils/format';

const INDEX_TABS = [
  { key: 'composite', label: 'Composite' },
  { key: 'value', label: 'Value' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'quality', label: 'Quality' },
  { key: 'lowvol', label: 'Low Vol' },
] as const;

export function IndexPreview() {
  const [activeIndex, setActiveIndex] = useState<string>('composite');

  const chartData = (mockIndexData[activeIndex] || []).map((bar) => ({
    time: bar.timestamp.split('T')[0],
    value: bar.close,
  }));

  return (
    <section className="bg-bg-secondary py-24 md:py-32">
      <div className="mx-auto max-w-content px-6">
        <h2 className="font-display text-3xl text-text-primary md:text-4xl">
          Pyhron Factor Indices
        </h2>
        <p className="mt-4 text-text-secondary">
          Systematic factor indices tracking value, momentum, quality, and low-volatility
          premia in IDX equities.
        </p>

        <div className="mt-8 flex flex-wrap gap-2">
          {INDEX_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveIndex(tab.key)}
              className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                activeIndex === tab.key
                  ? 'bg-accent-500 text-primary-900'
                  : 'text-text-secondary hover:bg-bg-tertiary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="mt-6">
          <StockChart data={chartData} height={400} />
        </div>

        <div className="mt-8 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-3 text-left font-medium text-text-muted">Index</th>
                <th className="py-3 text-right font-medium text-text-muted">Level</th>
                <th className="py-3 text-right font-medium text-text-muted">1D</th>
                <th className="py-3 text-right font-medium text-text-muted">1W</th>
                <th className="py-3 text-right font-medium text-text-muted">1M</th>
                <th className="py-3 text-right font-medium text-text-muted">YTD</th>
                <th className="py-3 text-right font-medium text-text-muted">1Y</th>
              </tr>
            </thead>
            <tbody>
              {mockIndexPerformance.map((row) => (
                <tr key={row.index} className="border-b border-border last:border-0">
                  <td className="py-3 font-medium text-text-primary">{row.index}</td>
                  <td className="py-3 text-right font-mono text-text-secondary">{row.level.toFixed(2)}</td>
                  <td className={`py-3 text-right font-mono ${pctColor(row.d1)}`}>{formatPct(row.d1)}</td>
                  <td className={`py-3 text-right font-mono ${pctColor(row.w1)}`}>{formatPct(row.w1)}</td>
                  <td className={`py-3 text-right font-mono ${pctColor(row.m1)}`}>{formatPct(row.m1)}</td>
                  <td className={`py-3 text-right font-mono ${pctColor(row.ytd)}`}>{formatPct(row.ytd)}</td>
                  <td className={`py-3 text-right font-mono ${pctColor(row.y1)}`}>{formatPct(row.y1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
