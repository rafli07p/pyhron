'use client';

import { useState, useMemo } from 'react';
import { StockChart } from '@/components/charts/StockChart';
import { MonthlyReturnsHeatmap } from '@/components/charts/MonthlyReturnsHeatmap';
import { SectorPieChart } from '@/components/charts/SectorPieChart';
import { SectorTreemap } from '@/components/charts/SectorTreemap';
import { mockIndexData, mockIndexPerformance } from '@/lib/mock/data/indices';
import { formatPct, pctColor } from '@/lib/utils/format';

const indices = [
  { key: 'composite', label: 'Pyhron Composite' },
  { key: 'value', label: 'Pyhron Value' },
  { key: 'momentum', label: 'Pyhron Momentum' },
  { key: 'quality', label: 'Pyhron Quality' },
  { key: 'lowvol', label: 'Pyhron Low Vol' },
];

const metrics = [
  { label: 'CAGR', value: '12.4%' },
  { label: 'Volatility', value: '18.2%' },
  { label: 'Sharpe', value: '0.68' },
  { label: 'Sortino', value: '0.95' },
  { label: 'Max Drawdown', value: '-22.1%' },
  { label: 'Calmar', value: '0.56' },
];

function computeMonthlyReturns(data: { timestamp: string; close: number }[]) {
  const monthlyMap = new Map<string, { first: number; last: number }>();
  for (const bar of data) {
    const date = bar.timestamp.split('T')[0];
    const key = date.substring(0, 7);
    const entry = monthlyMap.get(key);
    if (!entry) {
      monthlyMap.set(key, { first: bar.close, last: bar.close });
    } else {
      entry.last = bar.close;
    }
  }
  const returns: { year: number; month: number; value: number }[] = [];
  for (const [key, val] of monthlyMap) {
    const [yearStr, monthStr] = key.split('-');
    const ret = ((val.last - val.first) / val.first) * 100;
    returns.push({ year: parseInt(yearStr), month: parseInt(monthStr), value: Math.round(ret * 10) / 10 });
  }
  return returns;
}

export function IndexDashboard() {
  const [selectedIndex, setSelectedIndex] = useState('composite');

  const indexData = mockIndexData[selectedIndex] || [];

  const chartData = indexData.map((bar) => ({
    time: bar.timestamp.split('T')[0],
    value: bar.close,
  }));

  const monthlyReturns = useMemo(() => computeMonthlyReturns(indexData), [indexData]);

  const handleExportCSV = () => {
    const today = new Date().toISOString().split('T')[0];
    const csv = ['Date,Open,High,Low,Close,Volume']
      .concat(indexData.map((d) => `${d.timestamp.split('T')[0]},${d.open},${d.high},${d.low},${d.close},${d.volume}`))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pyhron-${selectedIndex}-${today}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={selectedIndex}
          onChange={(e) => setSelectedIndex(e.target.value)}
          className="rounded-md border border-border bg-bg-primary px-3 py-2 text-sm focus:border-accent-500 focus:outline-none"
        >
          {indices.map((idx) => (
            <option key={idx.key} value={idx.key}>{idx.label}</option>
          ))}
        </select>
        <button
          onClick={handleExportCSV}
          className="rounded-md border border-border px-4 py-2 text-sm text-text-secondary hover:bg-bg-tertiary transition-colors"
        >
          Export CSV
        </button>
      </div>

      <StockChart data={chartData} height={450} />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-border bg-bg-secondary p-4">
            <p className="text-xs text-text-muted">{m.label}</p>
            <p className="mt-1 text-lg font-medium font-mono text-text-primary">{m.value}</p>
          </div>
        ))}
      </div>

      <div>
        <h3 className="text-lg font-medium text-text-primary mb-4">Performance Summary</h3>
        <div className="overflow-x-auto">
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
                <tr key={row.index} className="border-b border-border last:border-0 hover:bg-bg-secondary">
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

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-bg-secondary p-6">
          <h3 className="text-sm font-medium text-text-muted mb-4">Sector Allocation</h3>
          <SectorPieChart />
        </div>
        <div className="rounded-lg border border-border bg-bg-secondary p-6">
          <h3 className="text-sm font-medium text-text-muted mb-4">Sector Heatmap</h3>
          <SectorTreemap />
        </div>
      </div>

      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">Monthly Returns Heatmap</h3>
        <MonthlyReturnsHeatmap data={monthlyReturns} />
      </div>
    </div>
  );
}
