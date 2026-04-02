'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Input } from '@/design-system/primitives/Input';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

const CONDITION_TYPES = [
  'Price Above',
  'Price Below',
  'Volume Spike',
  'Drawdown Exceeds',
  'Signal Generated',
];

const SYMBOLS = ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'UNVR', 'GOTO', 'BRIS'];

const COOLDOWNS = [
  { value: '15m', label: '15 minutes' },
  { value: '1h', label: '1 hour' },
  { value: '4h', label: '4 hours' },
  { value: '24h', label: '24 hours' },
];

export default function NewAlertPage() {
  return (
    <TierGate requiredTier="strategist" featureName="Alerts">
      <div className="space-y-6">
        <PageHeader
          title="Create Alert"
          description="Set up a new market condition alert"
          actions={
            <Link href="/alerts">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
                Back to Alerts
              </Button>
            </Link>
          }
        />

        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle>Alert Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
              <Input label="Alert Name" placeholder="e.g. BBCA Price Drop" />

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--text-secondary)]">
                  Condition Type
                </label>
                <select className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]">
                  <option value="">Select condition...</option>
                  {CONDITION_TYPES.map((ct) => (
                    <option key={ct} value={ct}>
                      {ct}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--text-secondary)]">Symbol</label>
                <select className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]">
                  <option value="">Select symbol...</option>
                  {SYMBOLS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <Input label="Threshold" type="number" placeholder="e.g. 9500" />

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--text-secondary)]">
                  Notify Via
                </label>
                <div className="flex gap-4">
                  {['In-app', 'Email', 'Webhook'].map((channel) => (
                    <label
                      key={channel}
                      className="flex items-center gap-2 text-sm text-[var(--text-primary)]"
                    >
                      <input
                        type="checkbox"
                        defaultChecked={channel === 'In-app'}
                        className="h-4 w-4 rounded border-[var(--border-default)] bg-[var(--surface-2)] accent-[var(--accent-500)]"
                      />
                      {channel}
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--text-secondary)]">
                  Cooldown Period
                </label>
                <select className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]">
                  {COOLDOWNS.map((cd) => (
                    <option key={cd.value} value={cd.value}>
                      {cd.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2">
                <Button type="submit" className="w-full">
                  Create Alert
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </TierGate>
  );
}
