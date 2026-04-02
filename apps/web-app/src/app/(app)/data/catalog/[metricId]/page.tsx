'use client';

import Link from 'next/link';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { TierBadge } from '@/components/common/TierGate';
import { ArrowLeft, Plus, Copy } from 'lucide-react';

const SAMPLE_METRIC = {
  id: 'rsi-14',
  name: 'RSI (14)',
  category: 'Technical Indicators',
  tier: 'explorer' as const,
  description:
    'The Relative Strength Index (RSI) is a momentum oscillator that measures the speed and magnitude of recent price changes. A 14-period RSI is the most commonly used configuration.',
  coverage: '900+ stocks',
  history: 'Jan 2015 - Present',
  updateFrequency: 'End of day (T+0, 17:30 WIB)',
  dataType: 'Float (0-100)',
  apiEndpoint: '/api/v1/metrics/rsi-14',
  sampleRequest: 'GET /api/v1/metrics/rsi-14?symbol=BBCA&start=2026-01-01&end=2026-03-31',
  sampleResponse: '{ "symbol": "BBCA", "metric": "rsi-14", "data": [{ "date": "2026-03-31", "value": 58.42 }, ...] }',
};

export default function MetricDetailPage() {
  const metric = SAMPLE_METRIC;

  return (
    <div className="space-y-6">
      <PageHeader
        title={metric.name}
        description={metric.category}
        actions={
          <div className="flex items-center gap-2">
            <TierBadge tier={metric.tier} />
            <Button size="sm">
              <Plus className="h-4 w-4" />
              Add to Workbench
            </Button>
            <Link href="/data/catalog">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-[var(--text-secondary)]">{metric.description}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Chart Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex h-64 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
                Chart loads with lightweight-charts
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API Endpoint</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded-md bg-[var(--surface-2)] px-3 py-2 font-mono text-xs text-[var(--text-primary)]">
                  {metric.apiEndpoint}
                </code>
                <Button variant="ghost" size="icon">
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <div>
                <p className="mb-1 text-xs font-medium text-[var(--text-tertiary)]">Sample Request</p>
                <code className="block rounded-md bg-[var(--surface-2)] px-3 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {metric.sampleRequest}
                </code>
              </div>
              <div>
                <p className="mb-1 text-xs font-medium text-[var(--text-tertiary)]">Sample Response</p>
                <code className="block rounded-md bg-[var(--surface-2)] px-3 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {metric.sampleResponse}
                </code>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Coverage</dt>
                  <dd className="mt-0.5 text-sm text-[var(--text-primary)]">{metric.coverage}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">History Range</dt>
                  <dd className="mt-0.5 text-sm text-[var(--text-primary)]">{metric.history}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Update Frequency</dt>
                  <dd className="mt-0.5 text-sm text-[var(--text-primary)]">{metric.updateFrequency}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Data Type</dt>
                  <dd className="mt-0.5 text-sm text-[var(--text-primary)]">{metric.dataType}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Required Tier</dt>
                  <dd className="mt-1">
                    <TierBadge tier={metric.tier} />
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
