'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Input } from '@/design-system/primitives/Input';
import { Button } from '@/design-system/primitives/Button';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

const INSTITUTION_TYPES = [
  'Individual / Retail',
  'Family Office',
  'Proprietary Trading Firm',
  'Hedge Fund',
  'Asset Manager',
  'Other',
];

const EXPERIENCE_LEVELS = [
  'Less than 1 year',
  '1-3 years',
  '3-5 years',
  '5-10 years',
  '10+ years',
];

const AUM_RANGES = [
  'Under IDR 100M',
  'IDR 100M - 500M',
  'IDR 500M - 1B',
  'IDR 1B - 5B',
  'IDR 5B - 25B',
  'Above IDR 25B',
];

const STRATEGY_TYPES = [
  'Momentum',
  'Mean Reversion',
  'Statistical Arbitrage',
  'Pairs Trading',
  'Factor-based',
  'ML / AI-driven',
  'Market Making',
  'Event-driven',
];

export default function RequestAccessPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Request Live Access"
        description="Apply for Operator tier and live trading capabilities"
        actions={
          <Link href="/execution">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
              Back to Execution
            </Button>
          </Link>
        }
      />

      <Card className="mx-auto max-w-2xl">
        <CardHeader>
          <CardTitle>Live Trading Application</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                Institution Type
              </label>
              <select className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]">
                <option value="">Select type...</option>
                {INSTITUTION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                Trading Experience
              </label>
              <select className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]">
                <option value="">Select experience level...</option>
                {EXPERIENCE_LEVELS.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                AUM Range
              </label>
              <select className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]">
                <option value="">Select range...</option>
                {AUM_RANGES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                Strategy Types
              </label>
              <div className="grid grid-cols-2 gap-2">
                {STRATEGY_TYPES.map((st) => (
                  <label
                    key={st}
                    className="flex items-center gap-2 text-sm text-[var(--text-primary)]"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-[var(--border-default)] bg-[var(--surface-2)] accent-[var(--accent-500)]"
                    />
                    {st}
                  </label>
                ))}
              </div>
            </div>

            <Input
              label="Expected Monthly Volume (IDR)"
              type="text"
              placeholder="e.g. 500,000,000"
            />

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                Trading Approach
              </label>
              <textarea
                rows={4}
                placeholder="Describe your trading strategy, risk management approach, and how you plan to use Pyhron..."
                className="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]"
              />
            </div>

            <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] p-4">
              <label className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-[var(--border-default)] bg-[var(--surface-2)] accent-[var(--accent-500)]"
                />
                <span>
                  I acknowledge that algorithmic trading involves substantial risk of loss,
                  including the possibility of losing all invested capital. I have read and
                  understand the{' '}
                  <a href="#" className="text-[var(--accent-500)] hover:underline">
                    Risk Disclosure
                  </a>{' '}
                  and{' '}
                  <a href="#" className="text-[var(--accent-500)] hover:underline">
                    Terms of Service
                  </a>
                  .
                </span>
              </label>
            </div>

            <div className="pt-2">
              <Button type="submit" className="w-full">
                Submit Application
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
