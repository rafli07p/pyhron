'use client';

import { useState, useMemo } from 'react';
import { STRATEGIES } from '@/mocks/terminal-data';
import { TerminalDisclaimer } from '@/components/terminal/TerminalDisclaimer';

type SortKey = 'name' | 'type' | 'pnl' | 'sharpe' | 'maxDd' | 'trades';
type SortDir = 'asc' | 'desc';
type Filter = 'all' | 'running' | 'paused' | 'error';

const STATUS_DOT: Record<string, string> = {
  running: 'text-emerald-400',
  paused: 'text-amber-400',
  error: 'text-red-400',
};
const STATUS_ICON: Record<string, string> = {
  running: '●',
  paused: '○',
  error: '✕',
};

const counts = {
  all: STRATEGIES.length,
  running: STRATEGIES.filter((s) => s.status === 'running').length,
  paused: STRATEGIES.filter((s) => s.status === 'paused').length,
  error: STRATEGIES.filter((s) => s.status === 'error').length,
};

export default function StrategiesPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('asc'); }
  };

  const rows = useMemo(() => {
    const filtered = filter === 'all' ? [...STRATEGIES] : STRATEGIES.filter((s) => s.status === filter);
    return [...filtered].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filter, sortKey, sortDir]);

  const hdr = (label: string, key?: SortKey) => (
    <th
      className={`px-3 py-2 text-left text-[10px] uppercase tracking-wider text-white/30 ${key ? 'cursor-pointer select-none hover:text-white/50' : ''}`}
      onClick={key ? () => toggleSort(key) : undefined}
    >
      {label}
      {key && sortKey === key && <span className="ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>}
    </th>
  );

  const filters: { key: Filter; label: string }[] = [
    { key: 'all', label: `All (${counts.all})` },
    { key: 'running', label: `Running (${counts.running})` },
    { key: 'paused', label: `Paused (${counts.paused})` },
    { key: 'error', label: `Error (${counts.error})` },
  ];

  return (
    <div className="flex min-h-full flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-semibold text-white/90">Strategies</h1>
        <button className="rounded-md border border-white/10 px-3 py-1 text-xs text-white/60 hover:bg-white/[0.04]">
          + New Strategy
        </button>
      </div>

      <div className="flex gap-1">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-md px-3 py-1 text-xs transition-colors ${
              filter === f.key ? 'bg-white/[0.08] text-white/80' : 'text-white/30 hover:text-white/50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-[#1e1e22]">
        <table className="w-full text-xs text-white/70">
          <thead className="border-b border-[#1e1e22] bg-white/[0.02]">
            <tr>
              <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider text-white/30">Status</th>
              {hdr('Name', 'name')}
              {hdr('Type', 'type')}
              {hdr('P&L%', 'pnl')}
              {hdr('Sharpe', 'sharpe')}
              {hdr('Max DD', 'maxDd')}
              {hdr('Trades', 'trades')}
              <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider text-white/30">Mode</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="border-b border-[#1e1e22] hover:bg-white/[0.02]">
                <td className="px-3 py-2.5">
                  <span className={STATUS_DOT[s.status]}>{STATUS_ICON[s.status]}</span>
                </td>
                <td className="px-3 py-2.5 font-medium text-white/90">{s.name}</td>
                <td className="px-3 py-2.5 text-white/40">{s.type}</td>
                <td className={`px-3 py-2.5 font-mono ${s.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {s.pnl >= 0 ? '+' : ''}{s.pnl.toFixed(1)}%
                </td>
                <td className="px-3 py-2.5 font-mono">{s.sharpe.toFixed(2)}</td>
                <td className="px-3 py-2.5 font-mono text-red-400/70">{s.maxDd.toFixed(1)}%</td>
                <td className="px-3 py-2.5 font-mono">{s.trades}</td>
                <td className="px-3 py-2.5">
                  <span className="rounded border border-blue-400/30 px-1.5 py-0.5 text-[10px] text-blue-400">
                    {s.mode}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <TerminalDisclaimer />
    </div>
  );
}
