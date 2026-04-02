'use client';

import { useState } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { Play, FlaskConical } from 'lucide-react';

const strategyTypes = [
  'Momentum',
  'Mean Reversion',
  'Pairs Trading',
  'Value Factor',
  'Sector Rotation',
  'Custom',
];

const inputClass =
  'w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent-500)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-500)]';

export default function NewBacktestPage() {
  const { hasAccess } = useTierGate('studio.backtests');
  const [symbols, setSymbols] = useState('');

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <PageHeader title="New Backtest" description="Configure and launch a strategy backtest" />
        <TierGate requiredTier="strategist" featureName="Backtesting" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Backtest"
        description="Configure and launch a strategy backtest"
      />

      <Card className="mx-auto max-w-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-3.5 w-3.5" />
            Backtest Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Strategy Type
              </label>
              <select className={inputClass}>
                {strategyTypes.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Symbols (comma-separated)
              </label>
              <input
                type="text"
                placeholder="e.g. BBCA, BMRI, TLKM, ASII"
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
                className={inputClass}
              />
              {symbols && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {symbols.split(',').map((s) => s.trim()).filter(Boolean).map((s) => (
                    <span
                      key={s}
                      className="rounded bg-[var(--surface-3)] px-2 py-0.5 text-xs text-[var(--text-secondary)]"
                    >
                      {s.toUpperCase()}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                  Start Date
                </label>
                <input type="date" defaultValue="2024-01-01" className={inputClass} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                  End Date
                </label>
                <input type="date" defaultValue="2025-12-31" className={inputClass} />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Initial Capital (IDR)
              </label>
              <input
                type="text"
                defaultValue="1,000,000,000"
                className={inputClass}
              />
            </div>

            <Button variant="primary" size="md" className="w-full">
              <Play className="h-3.5 w-3.5" />
              Launch Backtest
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
