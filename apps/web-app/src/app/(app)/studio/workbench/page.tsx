'use client';

import { useState } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import {
  Save,
  Share2,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Settings,
  Layers,
} from 'lucide-react';

const timeframes = ['1D', '1W', '1M', '3M', '1Y', '5Y'] as const;

const metricCategories = [
  {
    name: 'Price',
    items: ['Close', 'Open', 'High', 'Low', 'VWAP'],
  },
  {
    name: 'Volume',
    items: ['Volume', 'Dollar Volume', 'Relative Volume'],
  },
  {
    name: 'Fundamentals',
    items: ['P/E Ratio', 'P/B Ratio', 'ROE', 'ROA', 'EPS'],
  },
  {
    name: 'Technical',
    items: ['SMA 20', 'SMA 50', 'RSI 14', 'MACD', 'Bollinger Bands'],
  },
  {
    name: 'Macro',
    items: ['BI Rate', 'Inflation YoY', 'USD/IDR', 'IHSG'],
  },
];

const transforms = ['Raw', 'Log', 'YoY %', 'MoM %', 'Z-Score', 'Rank', 'Diff'];

export default function WorkbenchPage() {
  const { hasAccess } = useTierGate('studio.workbench.create');
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('1Y');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['Price']));

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <PageHeader title="Workbench" description="Interactive charting and metric exploration" />
        <TierGate requiredTier="strategist" featureName="Workbench" />
      </div>
    );
  }

  function toggleCategory(name: string) {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Workbench"
        description="Interactive charting and metric exploration"
        actions={
          <>
            <Button variant="outline" size="sm">
              <Share2 className="h-3.5 w-3.5" />
              Share
            </Button>
            <Button variant="primary" size="sm">
              <Save className="h-3.5 w-3.5" />
              Save
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[240px_1fr]">
        {/* Metric Browser Sidebar */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-3.5 w-3.5" />
              Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {metricCategories.map((cat) => (
                <div key={cat.name}>
                  <button
                    onClick={() => toggleCategory(cat.name)}
                    className="flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-3)]"
                  >
                    {expandedCategories.has(cat.name) ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    {cat.name}
                  </button>
                  {expandedCategories.has(cat.name) && (
                    <div className="ml-4 space-y-0.5">
                      {cat.items.map((item) => (
                        <button
                          key={item}
                          className="block w-full rounded px-2 py-1 text-left text-xs text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Main Chart Area */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-3.5 w-3.5" />
                  Chart
                </CardTitle>
                <div className="flex gap-1">
                  {timeframes.map((tf) => (
                    <button
                      key={tf}
                      onClick={() => setSelectedTimeframe(tf)}
                      className={`rounded px-2 py-0.5 text-xs transition-colors ${
                        selectedTimeframe === tf
                          ? 'bg-[var(--accent-500)] text-white'
                          : 'text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex h-80 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
                Select a metric to begin
              </div>
            </CardContent>
          </Card>

          {/* Bottom: Transforms & Settings */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-3.5 w-3.5" />
                  Transforms
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5">
                  {transforms.map((t) => (
                    <button
                      key={t}
                      className="rounded-md border border-[var(--border-default)] px-2.5 py-1 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-3)]"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-3.5 w-3.5" />
                  Settings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-xs text-[var(--text-secondary)]">
                  <div className="flex items-center justify-between">
                    <span>Chart Type</span>
                    <span className="text-[var(--text-tertiary)]">Line</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Normalization</span>
                    <span className="text-[var(--text-tertiary)]">None</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Benchmark</span>
                    <span className="text-[var(--text-tertiary)]">IHSG</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
