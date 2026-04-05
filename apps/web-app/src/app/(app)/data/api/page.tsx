'use client';

import { useState } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { Key, Eye, EyeOff, Trash2, Plus, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsed: string;
  status: 'active' | 'revoked';
}

const SAMPLE_KEYS: ApiKey[] = [
  { id: '1', name: 'Production Key', prefix: 'phr_live_a3f2...', createdAt: '2026-03-01', lastUsed: '2026-04-01', status: 'active' },
  { id: '2', name: 'Development Key', prefix: 'phr_dev_8b1c...', createdAt: '2026-02-15', lastUsed: '2026-03-28', status: 'active' },
  { id: '3', name: 'Old Key', prefix: 'phr_live_f9d1...', createdAt: '2025-12-01', lastUsed: '2026-01-15', status: 'revoked' },
];

const ENDPOINTS = [
  { method: 'GET', path: '/api/v1/metrics/{metricId}', description: 'Retrieve metric values for a symbol' },
  { method: 'GET', path: '/api/v1/metrics', description: 'List all available metrics' },
  { method: 'GET', path: '/api/v1/universe/{universe}', description: 'List stocks in a universe (LQ45, IDX80, etc.)' },
  { method: 'GET', path: '/api/v1/prices/{symbol}', description: 'Historical OHLCV price data' },
  { method: 'GET', path: '/api/v1/signals', description: 'Active ML signals and factor scores' },
  { method: 'GET', path: '/api/v1/fundamentals/{symbol}', description: 'Fundamental data (P/E, ROE, etc.)' },
  { method: 'POST', path: '/api/v1/query', description: 'Execute a data query (Data Explorer)' },
  { method: 'GET', path: '/api/v1/export/{format}', description: 'Export data as CSV or Parquet' },
];

const RATE_LIMITS: Record<string, { requests: string; burst: string }> = {
  explorer: { requests: '100 / hour', burst: '10 / min' },
  strategist: { requests: '1,000 / hour', burst: '50 / min' },
  operator: { requests: 'Unlimited', burst: '200 / min' },
};

export default function DataApiPage() {
  const { userTier } = useTierGate('data.api');
  const rateLimit = RATE_LIMITS[userTier] ?? RATE_LIMITS.explorer!;
  const [showKey, setShowKey] = useState<string | null>(null);

  return (
    <TierGate requiredTier="strategist" featureName="Data API">
      <div className="space-y-3">
        <PageHeader
          title="Data API"
          description="Manage API keys and explore available endpoints"
          actions={
            <Link href="/data">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
                Back to Data
              </Button>
            </Link>
          }
        />

        {/* API Key Management */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>API Keys</CardTitle>
              <Button size="sm">
                <Plus className="h-4 w-4" />
                Create Key
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="grid grid-cols-5 gap-2 px-2 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                <span>Name</span>
                <span>Key</span>
                <span>Created</span>
                <span>Last Used</span>
                <span>Actions</span>
              </div>
              {SAMPLE_KEYS.map((key) => (
                <div
                  key={key.id}
                  className="grid grid-cols-5 items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-[var(--surface-3)]"
                >
                  <div className="flex items-center gap-2">
                    <Key className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                    <span className="font-medium text-[var(--text-primary)]">{key.name}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <code className="font-mono text-xs text-[var(--text-secondary)]">
                      {showKey === key.id ? 'phr_live_a3f2b8c1d9e4f7' : key.prefix}
                    </code>
                    <button
                      onClick={() => setShowKey(showKey === key.id ? null : key.id)}
                      className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
                    >
                      {showKey === key.id ? (
                        <EyeOff className="h-3.5 w-3.5" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                  <span className="text-xs text-[var(--text-tertiary)]">{key.createdAt}</span>
                  <span className="text-xs text-[var(--text-tertiary)]">{key.lastUsed}</span>
                  <div className="flex items-center gap-1">
                    <Badge variant={key.status === 'active' ? 'positive' : 'default'}>
                      {key.status}
                    </Badge>
                    {key.status === 'active' && (
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <Trash2 className="h-3.5 w-3.5 text-[var(--negative)]" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Rate Limits */}
        <Card>
          <CardHeader>
            <CardTitle>Rate Limits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Your Tier
                </p>
                <p className="mt-1 text-sm font-medium capitalize text-[var(--text-primary)]">
                  {userTier}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Requests
                </p>
                <p className="mt-1 text-sm text-[var(--text-primary)]">{rateLimit.requests}</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
                  Burst Limit
                </p>
                <p className="mt-1 text-sm text-[var(--text-primary)]">{rateLimit.burst}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Reference */}
        <Card>
          <CardHeader>
            <CardTitle>Endpoint Reference</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {ENDPOINTS.map((ep) => (
                <div
                  key={ep.path}
                  className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-[var(--surface-3)]"
                >
                  <Badge
                    variant={ep.method === 'GET' ? 'positive' : 'info'}
                    className="w-12 justify-center font-mono"
                  >
                    {ep.method}
                  </Badge>
                  <code className="shrink-0 font-mono text-xs text-[var(--text-primary)]">
                    {ep.path}
                  </code>
                  <span className="text-xs text-[var(--text-tertiary)]">{ep.description}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </TierGate>
  );
}
