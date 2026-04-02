'use client';

import { useState } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { Badge } from '@/design-system/primitives/Badge';
import { Plus, LayoutDashboard, Copy, Clock } from 'lucide-react';
import Link from 'next/link';

const tabs = ['My Dashboards', 'Curated'] as const;

const myDashboards = [
  { id: 'dash-1', name: 'Portfolio Overview', tiles: 8, updatedAt: '2 hours ago' },
  { id: 'dash-2', name: 'Banking Sector', tiles: 6, updatedAt: '1 day ago' },
  { id: 'dash-3', name: 'Watchlist Monitor', tiles: 4, updatedAt: '3 days ago' },
];

const curatedDashboards = [
  { id: 'cur-1', name: 'IDX Market Overview', description: 'Broad market indices, top movers, and sector performance', tiles: 12 },
  { id: 'cur-2', name: 'LQ45 Monitor', description: 'Real-time tracking of LQ45 constituents', tiles: 10 },
  { id: 'cur-3', name: 'Macro Indonesia', description: 'BI rate, inflation, rupiah, bonds, and commodity prices', tiles: 8 },
  { id: 'cur-4', name: 'Sector Comparison', description: 'Side-by-side sector fundamentals and momentum', tiles: 9 },
];

export default function DashboardsPage() {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>('My Dashboards');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboards"
        description="Create and manage analytical dashboards"
        actions={
          <Link href="/studio/dashboards/new">
            <Button variant="primary" size="sm">
              <Plus className="h-3.5 w-3.5" />
              New Dashboard
            </Button>
          </Link>
        }
      />

      <div className="flex gap-1 border-b border-[var(--border-default)]">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'border-[var(--accent-500)] text-[var(--accent-500)]'
                : 'border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'My Dashboards' && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {myDashboards.map((d) => (
            <Link key={d.id} href={`/studio/dashboards/${d.id}`}>
              <Card className="group h-full cursor-pointer transition-colors hover:border-[var(--accent-500)]">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <LayoutDashboard className="h-3.5 w-3.5 text-[var(--accent-500)]" />
                      {d.name}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-tertiary)]">
                    <span>{d.tiles} tiles</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {d.updatedAt}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {activeTab === 'Curated' && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {curatedDashboards.map((d) => (
            <Card key={d.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <LayoutDashboard className="h-3.5 w-3.5 text-[var(--accent-500)]" />
                    {d.name}
                  </CardTitle>
                  <Badge variant="info">{d.tiles} tiles</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-[var(--text-secondary)]">{d.description}</p>
                <div className="flex gap-2">
                  <Link href={`/studio/dashboards/${d.id}`}>
                    <Button variant="ghost" size="sm">View</Button>
                  </Link>
                  <Button variant="outline" size="sm">
                    <Copy className="h-3 w-3" />
                    Clone
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
