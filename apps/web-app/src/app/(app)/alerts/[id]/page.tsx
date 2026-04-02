'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { EmptyState } from '@/design-system/data-display/EmptyState';
import { TierGate } from '@/components/common/TierGate';
import { ArrowLeft, Pencil, Trash2, Bell, BellRing } from 'lucide-react';
import Link from 'next/link';

const SAMPLE_ALERT = {
  id: '1',
  name: 'BBCA Price Drop',
  status: 'active' as const,
  conditionType: 'Price Below',
  symbol: 'BBCA',
  threshold: 'IDR 9,500',
  channels: ['in-app', 'email'] as const,
  cooldown: '1 hour',
  createdAt: '2026-03-28 09:15',
  triggers: [
    { id: 't1', triggeredAt: '2026-04-01 14:32', value: 'IDR 9,480', notified: true },
    { id: 't2', triggeredAt: '2026-03-30 10:15', value: 'IDR 9,495', notified: true },
  ],
};

const STATUS_VARIANT = {
  active: 'positive',
  triggered: 'warning',
  paused: 'default',
} as const;

export default function AlertDetailPage() {
  const alert = SAMPLE_ALERT;

  return (
    <TierGate requiredTier="strategist" featureName="Alerts">
      <div className="space-y-6">
        <PageHeader
          title={alert.name}
          description={`Created ${alert.createdAt}`}
          actions={
            <div className="flex items-center gap-2">
              <Badge variant={STATUS_VARIANT[alert.status]}>{alert.status}</Badge>
              <Button variant="outline" size="sm">
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </Button>
              <Button variant="danger" size="sm">
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
              <Link href="/alerts">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
              </Link>
            </div>
          }
        />

        <Card>
          <CardHeader>
            <CardTitle>Condition Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Condition
                </p>
                <p className="mt-1 text-sm text-[var(--text-primary)]">{alert.conditionType}</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Symbol
                </p>
                <p className="mt-1 text-sm text-[var(--text-primary)]">{alert.symbol}</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Threshold
                </p>
                <p className="mt-1 text-sm text-[var(--text-primary)]">{alert.threshold}</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Channels
                </p>
                <div className="mt-1 flex gap-1">
                  {alert.channels.map((ch) => (
                    <Badge key={ch} variant="outline">
                      {ch}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Cooldown
                </p>
                <p className="mt-1 text-sm text-[var(--text-primary)]">{alert.cooldown}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Trigger History</CardTitle>
          </CardHeader>
          <CardContent>
            {alert.triggers.length === 0 ? (
              <EmptyState
                icon={Bell}
                title="No triggers yet"
                description="This alert has not been triggered."
              />
            ) : (
              <div className="space-y-1">
                <div className="grid grid-cols-3 gap-2 px-2 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  <span>Time</span>
                  <span>Value</span>
                  <span>Notified</span>
                </div>
                {alert.triggers.map((t) => (
                  <div
                    key={t.id}
                    className="grid grid-cols-3 gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-[var(--surface-3)]"
                  >
                    <span className="flex items-center gap-1.5 text-[var(--text-primary)]">
                      <BellRing className="h-3 w-3 text-[var(--warning)]" />
                      {t.triggeredAt}
                    </span>
                    <span className="tabular-nums text-[var(--text-secondary)]">{t.value}</span>
                    <Badge variant={t.notified ? 'positive' : 'default'}>
                      {t.notified ? 'sent' : 'pending'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </TierGate>
  );
}
