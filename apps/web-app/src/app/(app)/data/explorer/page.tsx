'use client';

import { useState } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { EmptyState } from '@/design-system/data-display/EmptyState';
import { Play, Save, Clock, Database } from 'lucide-react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

const SAVED_QUERIES = [
  { id: '1', name: 'LQ45 Volume Leaders', query: "SELECT symbol, volume_20d_avg FROM metrics WHERE universe = 'LQ45' ORDER BY volume_20d_avg DESC LIMIT 10", lastRun: '2026-04-01' },
  { id: '2', name: 'High RSI Stocks', query: "SELECT symbol, rsi_14, close_price FROM metrics WHERE rsi_14 > 70 AND universe = 'IDX80'", lastRun: '2026-03-30' },
  { id: '3', name: 'Low P/E Growth', query: "SELECT symbol, pe_ratio, roe FROM metrics WHERE pe_ratio < 15 AND roe > 0.15 ORDER BY roe DESC", lastRun: '2026-03-28' },
];

const SAMPLE_RESULTS = [
  { symbol: 'BBCA', volume_20d_avg: '12,456,800', rsi_14: '58.42', close_price: '9,875' },
  { symbol: 'BBRI', volume_20d_avg: '18,234,500', rsi_14: '62.10', close_price: '5,450' },
  { symbol: 'BMRI', volume_20d_avg: '9,876,300', rsi_14: '51.33', close_price: '6,225' },
  { symbol: 'TLKM', volume_20d_avg: '15,678,900', rsi_14: '44.87', close_price: '3,850' },
  { symbol: 'ASII', volume_20d_avg: '7,234,100', rsi_14: '55.21', close_price: '5,100' },
];

export default function DataExplorerPage() {
  const [query, setQuery] = useState(
    "SELECT symbol, close_price, volume_20d_avg, rsi_14\nFROM metrics\nWHERE universe = 'LQ45'\nORDER BY volume_20d_avg DESC\nLIMIT 10"
  );
  const [hasResults, setHasResults] = useState(false);

  return (
    <TierGate requiredTier="strategist" featureName="Data Explorer">
      <div className="space-y-3">
        <PageHeader
          title="Data Explorer"
          description="Query and explore datasets with a SQL-like interface"
          actions={
            <Link href="/data">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
                Back to Data
              </Button>
            </Link>
          }
        />

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Query Editor</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Save className="h-3.5 w-3.5" />
                  Save
                </Button>
                <Button size="sm" onClick={() => setHasResults(true)}>
                  <Play className="h-3.5 w-3.5" />
                  Run
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={6}
              spellCheck={false}
              className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-4 py-3 font-mono text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]"
              placeholder="SELECT * FROM metrics WHERE ..."
            />
          </CardContent>
        </Card>

        {hasResults ? (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Results</CardTitle>
                <span className="text-xs text-[var(--text-tertiary)]">5 rows returned in 0.23s</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-default)]">
                      {['symbol', 'close_price', 'volume_20d_avg', 'rsi_14'].map((col) => (
                        <th
                          key={col}
                          className="px-3 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {SAMPLE_RESULTS.map((row) => (
                      <tr
                        key={row.symbol}
                        className="border-b border-[var(--border-default)] last:border-0 hover:bg-[var(--surface-3)]"
                      >
                        <td className="px-3 py-2 font-medium text-[var(--text-primary)]">{row.symbol}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{row.close_price}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{row.volume_20d_avg}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{row.rsi_14}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="py-0">
              <EmptyState
                icon={Database}
                title="No results yet"
                description="Write a query and click Run to see results."
              />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Saved Queries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {SAVED_QUERIES.map((sq) => (
                <button
                  key={sq.id}
                  onClick={() => {
                    setQuery(sq.query);
                    setHasResults(false);
                  }}
                  className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left transition-colors hover:bg-[var(--surface-3)]"
                >
                  <div className="flex items-center gap-3">
                    <Clock className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                    <div>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{sq.name}</p>
                      <p className="mt-0.5 truncate font-mono text-xs text-[var(--text-tertiary)]">
                        {sq.query}
                      </p>
                    </div>
                  </div>
                  <span className="shrink-0 text-xs text-[var(--text-tertiary)]">{sq.lastRun}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </TierGate>
  );
}
