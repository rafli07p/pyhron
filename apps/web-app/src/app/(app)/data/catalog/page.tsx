'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { TierBadge } from '@/components/common/TierGate';
import type { Tier } from '@/constants/tiers';
import { Search, ArrowLeft } from 'lucide-react';
import { Button } from '@/design-system/primitives/Button';

interface Category {
  name: string;
  count: number;
}

const CATEGORIES: Category[] = [
  { name: 'Price & Volume', count: 24 },
  { name: 'Fundamentals', count: 18 },
  { name: 'Technical Indicators', count: 42 },
  { name: 'Factor Scores', count: 8 },
  { name: 'Valuation', count: 12 },
  { name: 'Risk Metrics', count: 15 },
  { name: 'ML Signals', count: 6 },
  { name: 'Macro', count: 8 },
  { name: 'Sector Aggregates', count: 11 },
];

interface Metric {
  id: string;
  name: string;
  description: string;
  coverage: string;
  category: string;
  tier: Tier;
}

const SAMPLE_METRICS: Metric[] = [
  { id: 'close-price', name: 'Close Price', description: 'End-of-day adjusted closing price', coverage: '900+ stocks', category: 'Price & Volume', tier: 'explorer' },
  { id: 'volume-20d-avg', name: 'Volume 20D Avg', description: '20-day rolling average daily volume', coverage: '900+ stocks', category: 'Price & Volume', tier: 'explorer' },
  { id: 'rsi-14', name: 'RSI (14)', description: '14-period Relative Strength Index', coverage: '900+ stocks', category: 'Technical Indicators', tier: 'explorer' },
  { id: 'macd', name: 'MACD', description: 'Moving Average Convergence Divergence signal line', coverage: '900+ stocks', category: 'Technical Indicators', tier: 'explorer' },
  { id: 'pe-ratio', name: 'P/E Ratio', description: 'Price-to-earnings ratio (TTM)', coverage: '700+ stocks', category: 'Valuation', tier: 'explorer' },
  { id: 'roe', name: 'ROE', description: 'Return on equity (trailing twelve months)', coverage: '700+ stocks', category: 'Fundamentals', tier: 'strategist' },
  { id: 'momentum-score', name: 'Momentum Score', description: 'Composite momentum factor combining price and volume signals', coverage: 'LQ45 + IDX80', category: 'Factor Scores', tier: 'strategist' },
  { id: 'ml-signal-v2', name: 'ML Signal v2', description: 'Ensemble ML prediction for 5-day forward returns', coverage: 'LQ45', category: 'ML Signals', tier: 'strategist' },
  { id: 'var-95', name: 'VaR 95%', description: '95th percentile Value at Risk (1-day horizon)', coverage: '500+ stocks', category: 'Risk Metrics', tier: 'strategist' },
  { id: 'beta-ihsg', name: 'Beta (IHSG)', description: 'Rolling 60-day beta relative to IHSG index', coverage: '900+ stocks', category: 'Risk Metrics', tier: 'explorer' },
  { id: 'bi-rate', name: 'BI Rate', description: 'Bank Indonesia benchmark interest rate', coverage: 'Macro', category: 'Macro', tier: 'explorer' },
  { id: 'sector-momentum', name: 'Sector Momentum', description: 'Relative sector momentum vs IHSG over 20 days', coverage: '11 sectors', category: 'Sector Aggregates', tier: 'strategist' },
];

const TOTAL_METRICS = CATEGORIES.reduce((sum, c) => sum + c.count, 0);

export default function MetricCatalogPage() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const filtered = SAMPLE_METRICS.filter((m) => {
    const matchesSearch =
      !search ||
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !selectedCategory || m.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Metric Catalog"
        description={`${TOTAL_METRICS} metrics available across ${CATEGORIES.length} categories`}
        actions={
          <Link href="/data">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
              Back to Data
            </Button>
          </Link>
        }
      />

      <div className="flex gap-6">
        {/* Sidebar */}
        <aside className="hidden w-56 shrink-0 lg:block">
          <div className="space-y-1">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`w-full rounded-md px-3 py-1.5 text-left text-sm transition-colors ${
                !selectedCategory
                  ? 'bg-[var(--accent-50)] font-medium text-[var(--accent-500)]'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]'
              }`}
            >
              All Metrics ({TOTAL_METRICS})
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat.name}
                onClick={() => setSelectedCategory(cat.name)}
                className={`w-full rounded-md px-3 py-1.5 text-left text-sm transition-colors ${
                  selectedCategory === cat.name
                    ? 'bg-[var(--accent-50)] font-medium text-[var(--accent-500)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]'
                }`}
              >
                {cat.name} ({cat.count})
              </button>
            ))}
          </div>
        </aside>

        {/* Main area */}
        <div className="min-w-0 flex-1 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
            <input
              type="text"
              placeholder="Search metrics..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] pl-9 pr-3 py-1 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] hover:border-[var(--border-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]"
            />
          </div>

          {/* Mobile category select */}
          <div className="lg:hidden">
            <select
              value={selectedCategory ?? ''}
              onChange={(e) => setSelectedCategory(e.target.value || null)}
              className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]"
            >
              <option value="">All Metrics ({TOTAL_METRICS})</option>
              {CATEGORIES.map((cat) => (
                <option key={cat.name} value={cat.name}>
                  {cat.name} ({cat.count})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((metric) => (
              <Link key={metric.id} href={`/data/catalog/${metric.id}`}>
                <Card className="h-full transition-colors hover:bg-[var(--surface-2)]">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <p className="text-sm font-semibold text-[var(--text-primary)]">
                        {metric.name}
                      </p>
                      <TierBadge tier={metric.tier} />
                    </div>
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                      {metric.description}
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <Badge variant="outline">{metric.coverage}</Badge>
                      <Badge variant="default">{metric.category}</Badge>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="mb-3 h-6 w-6 text-[var(--text-tertiary)]" />
              <p className="text-sm font-medium text-[var(--text-primary)]">No metrics found</p>
              <p className="mt-1 text-sm text-[var(--text-tertiary)]">
                Try adjusting your search or category filter.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
