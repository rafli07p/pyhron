'use client';

import { useState } from 'react';
import { MonthlyReturnsHeatmap } from '@/components/charts/MonthlyReturnsHeatmap';

const TICKERS = ['IHSG', 'BBCA', 'BBRI', 'TLKM', 'ADRO', 'ASII', 'BMRI', 'UNVR'] as const;

function generateMonthlyReturns(seed: number) {
  const data = [];
  for (let year = 2020; year <= 2025; year++) {
    for (let month = 1; month <= 12; month++) {
      const v = Math.sin(seed + year * 12 + month) * 6 + (Math.random() - 0.5) * 4;
      data.push({ year, month, value: Math.round(v * 10) / 10 });
    }
  }
  return data;
}

const dataByTicker: Record<string, ReturnType<typeof generateMonthlyReturns>> = {};
TICKERS.forEach((t, i) => {
  dataByTicker[t] = generateMonthlyReturns(i * 7);
});

export function DataExplorerView() {
  const [ticker, setTicker] = useState<string>('IHSG');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-medium text-text-primary">Data Explorer</h1>
        <select
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          className="rounded-md border border-border bg-bg-secondary px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-500"
        >
          {TICKERS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">
          Monthly Returns Heatmap &mdash; {ticker}
        </h3>
        <MonthlyReturnsHeatmap data={dataByTicker[ticker]} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-bg-secondary p-6">
          <h3 className="text-sm font-medium text-text-muted mb-4">Summary Statistics</h3>
          <div className="space-y-2 text-sm">
            {[
              { label: 'Mean Monthly Return', value: '0.82%' },
              { label: 'Monthly Std Dev', value: '4.15%' },
              { label: 'Best Month', value: '+12.3% (Nov 2020)' },
              { label: 'Worst Month', value: '-8.7% (Mar 2020)' },
              { label: 'Positive Months', value: '58.3%' },
              { label: 'Annualized Return', value: '10.2%' },
              { label: 'Max Drawdown', value: '-22.4%' },
            ].map((stat) => (
              <div key={stat.label} className="flex justify-between">
                <span className="text-text-secondary">{stat.label}</span>
                <span className="font-mono text-text-primary">{stat.value}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-bg-secondary p-6">
          <h3 className="text-sm font-medium text-text-muted mb-4">Correlation Matrix</h3>
          <div className="flex items-center justify-center h-[200px] text-text-muted text-sm">
            Select multiple tickers to view cross-correlation matrix
          </div>
        </div>
      </div>
    </div>
  );
}
