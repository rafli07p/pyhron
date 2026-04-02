'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { EmptyState } from '@/design-system/data-display/EmptyState';
import { TierGate } from '@/components/common/TierGate';
import { Bell, Plus, BellRing, Mail, Globe, Pause, Zap } from 'lucide-react';

type AlertStatus = 'active' | 'triggered' | 'paused';

interface Alert {
  id: string;
  name: string;
  condition: string;
  channels: ('in-app' | 'email' | 'webhook')[];
  status: AlertStatus;
  createdAt: string;
  triggeredAt?: string;
}

const SAMPLE_ALERTS: Alert[] = [
  {
    id: '1',
    name: 'BBCA Price Drop',
    condition: 'Price Below IDR 9,500',
    channels: ['in-app', 'email'],
    status: 'active',
    createdAt: '2026-03-28',
  },
  {
    id: '2',
    name: 'TLKM Volume Spike',
    condition: 'Volume Spike > 3x average',
    channels: ['in-app', 'webhook'],
    status: 'triggered',
    createdAt: '2026-03-25',
    triggeredAt: '2026-04-01 14:32',
  },
  {
    id: '3',
    name: 'Portfolio Drawdown',
    condition: 'Drawdown Exceeds 5%',
    channels: ['in-app', 'email', 'webhook'],
    status: 'active',
    createdAt: '2026-03-20',
  },
  {
    id: '4',
    name: 'BMRI Signal Alert',
    condition: 'Signal Generated for BMRI',
    channels: ['email'],
    status: 'paused',
    createdAt: '2026-03-15',
  },
];

const CHANNEL_ICONS = {
  'in-app': Bell,
  email: Mail,
  webhook: Globe,
} as const;

const STATUS_VARIANT = {
  active: 'positive',
  triggered: 'warning',
  paused: 'default',
} as const;

const TABS: { key: AlertStatus; label: string }[] = [
  { key: 'active', label: 'Active' },
  { key: 'triggered', label: 'Triggered' },
  { key: 'paused', label: 'Paused' },
];

export default function AlertsPage() {
  const [activeTab, setActiveTab] = useState<AlertStatus>('active');

  const filtered = SAMPLE_ALERTS.filter((a) => a.status === activeTab);

  return (
    <TierGate requiredTier="strategist" featureName="Alerts">
      <div className="space-y-6">
        <PageHeader
          title="Alerts"
          description="Monitor market conditions and get notified"
          actions={
            <Link href="/alerts/new">
              <Button size="sm">
                <Plus className="h-4 w-4" />
                New Alert
              </Button>
            </Link>
          }
        />

        <div className="flex gap-1 border-b border-[var(--border-default)]">
          {TABS.map((tab) => {
            const count = SAMPLE_ALERTS.filter((a) => a.status === tab.key).length;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'border-b-2 border-[var(--accent-500)] text-[var(--text-primary)]'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                }`}
              >
                {tab.label} ({count})
              </button>
            );
          })}
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={Bell}
            title={`No ${activeTab} alerts`}
            description={`You don't have any ${activeTab} alerts yet.`}
          />
        ) : (
          <div className="space-y-3">
            {filtered.map((alert) => (
              <Link key={alert.id} href={`/alerts/${alert.id}`}>
                <Card className="transition-colors hover:bg-[var(--surface-2)]">
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-4">
                      <div className="rounded-md bg-[var(--surface-2)] p-2">
                        {alert.status === 'triggered' ? (
                          <BellRing className="h-4 w-4 text-[var(--warning)]" />
                        ) : alert.status === 'paused' ? (
                          <Pause className="h-4 w-4 text-[var(--text-tertiary)]" />
                        ) : (
                          <Zap className="h-4 w-4 text-[var(--accent-500)]" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {alert.name}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
                          {alert.condition}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex gap-1">
                        {alert.channels.map((ch) => {
                          const Icon = CHANNEL_ICONS[ch];
                          return (
                            <Badge key={ch} variant="outline" className="gap-1">
                              <Icon className="h-3 w-3" />
                              {ch}
                            </Badge>
                          );
                        })}
                      </div>
                      <Badge variant={STATUS_VARIANT[alert.status]}>{alert.status}</Badge>
                      <span className="text-xs text-[var(--text-tertiary)]">{alert.createdAt}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </TierGate>
  );
}
