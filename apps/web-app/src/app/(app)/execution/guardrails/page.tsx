'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import {
  AlertTriangle,
  Power,
  ArrowLeft,
  TrendingDown,
  ShoppingCart,
  BarChart3,
} from 'lucide-react';
import Link from 'next/link';

const STAGE = 'week2' as const;
const STAGE_LABELS = {
  week1: 'Week 1 (Conservative)',
  week2: 'Week 2 (Standard)',
  full: 'Full Access',
} as const;

const STAGE_VARIANT = {
  week1: 'warning',
  week2: 'info',
  full: 'positive',
} as const;

const POSITION_LIMITS = [
  { name: 'Largest Position %', current: '8.2%', limit: '15%', status: 'ok' },
  { name: 'Largest Position IDR', current: 'IDR 82M', limit: 'IDR 150M', status: 'ok' },
  { name: 'Open Positions', current: '5', limit: '10', status: 'ok' },
];

const LOSS_LIMITS = [
  { name: 'Daily P&L', current: '-IDR 2.1M', limit: '-IDR 10M', status: 'ok' },
  { name: 'Daily P&L %', current: '-0.21%', limit: '-1.0%', status: 'ok' },
  { name: 'Current Drawdown', current: '2.8%', limit: '5.0%', status: 'warning' },
];

const ORDER_LIMITS = [
  { name: 'Orders Today', current: '12', limit: '50', status: 'ok' },
  { name: 'Orders / Minute', current: '0', limit: '5', status: 'ok' },
  { name: 'Largest Order', current: 'IDR 25M', limit: 'IDR 50M', status: 'ok' },
];

const BREACH_HISTORY = [
  {
    id: '1',
    type: 'Drawdown Warning',
    detail: 'Drawdown reached 4.2% (limit: 5.0%)',
    time: '2026-03-29 11:45',
    severity: 'warning',
  },
  {
    id: '2',
    type: 'Order Rate Limit',
    detail: 'Exceeded 5 orders/min for 3 seconds',
    time: '2026-03-25 14:02',
    severity: 'warning',
  },
  {
    id: '3',
    type: 'Position Size',
    detail: 'BBCA position attempted 18% (limit: 15%)',
    time: '2026-03-20 09:31',
    severity: 'negative',
  },
];

function LimitTable({
  title,
  icon: Icon,
  rows,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  rows: { name: string; current: string; limit: string; status: string }[];
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-[var(--accent-500)]" />
          <CardTitle>{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          <div className="grid grid-cols-3 gap-2 px-2 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            <span>Metric</span>
            <span>Current</span>
            <span>Limit</span>
          </div>
          {rows.map((row) => (
            <div
              key={row.name}
              className="grid grid-cols-3 items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-[var(--surface-3)]"
            >
              <span className="text-[var(--text-primary)]">{row.name}</span>
              <span
                className={`tabular-nums font-medium ${
                  row.status === 'warning'
                    ? 'text-[var(--warning)]'
                    : row.status === 'breach'
                      ? 'text-[var(--negative)]'
                      : 'text-[var(--text-secondary)]'
                }`}
              >
                {row.current}
              </span>
              <span className="tabular-nums text-[var(--text-tertiary)]">{row.limit}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function GuardrailsPage() {
  return (
    <TierGate requiredTier="operator" featureName="Risk Guardrails">
      <div className="space-y-6">
        <PageHeader
          title="Risk Guardrails"
          description="Real-time risk limits and circuit breakers"
          actions={
            <div className="flex items-center gap-2">
              <Badge variant={STAGE_VARIANT[STAGE]}>{STAGE_LABELS[STAGE]}</Badge>
              <Link href="/execution">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
              </Link>
            </div>
          }
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <LimitTable title="Position Limits" icon={BarChart3} rows={POSITION_LIMITS} />
          <LimitTable title="Loss Limits" icon={TrendingDown} rows={LOSS_LIMITS} />
          <LimitTable title="Order Limits" icon={ShoppingCart} rows={ORDER_LIMITS} />
        </div>

        {/* Kill Switch */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Power className="h-4 w-4 text-[var(--text-tertiary)]" />
                <CardTitle>Kill Switch</CardTitle>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-[var(--positive)]" />
                  <span className="text-xs text-[var(--text-tertiary)]">Inactive</span>
                </span>
                <Button variant="danger" size="sm">
                  <Power className="h-3.5 w-3.5" />
                  Activate Kill Switch
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-[var(--text-tertiary)]">
              Activating the kill switch will immediately cancel all open orders, close all
              positions at market, and disable all strategy execution. This action requires manual
              re-enablement and a cooldown period.
            </p>
          </CardContent>
        </Card>

        {/* Breach History */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-[var(--warning)]" />
              <CardTitle>Guardrail Breach History</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="grid grid-cols-4 gap-2 px-2 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                <span>Type</span>
                <span className="col-span-2">Detail</span>
                <span>Time</span>
              </div>
              {BREACH_HISTORY.map((breach) => (
                <div
                  key={breach.id}
                  className="grid grid-cols-4 items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-[var(--surface-3)]"
                >
                  <Badge
                    variant={
                      breach.severity === 'negative' ? 'negative' : 'warning'
                    }
                  >
                    {breach.type}
                  </Badge>
                  <span className="col-span-2 text-xs text-[var(--text-secondary)]">
                    {breach.detail}
                  </span>
                  <span className="text-xs text-[var(--text-tertiary)]">{breach.time}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </TierGate>
  );
}
