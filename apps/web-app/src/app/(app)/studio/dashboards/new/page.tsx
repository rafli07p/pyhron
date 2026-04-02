'use client';

import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import {
  Save,
  Eye,
  BarChart3,
  Hash,
  Table,
  Grid3X3,
  TrendingUp,
  PieChart,
  GripVertical,
} from 'lucide-react';

const tileTypes = [
  { name: 'Chart', icon: BarChart3, description: 'Line, bar, or candlestick chart' },
  { name: 'Stat Card', icon: Hash, description: 'Single metric with delta' },
  { name: 'Data Table', icon: Table, description: 'Tabular data display' },
  { name: 'Heatmap', icon: Grid3X3, description: 'Color-coded grid visualization' },
  { name: 'Sparkline', icon: TrendingUp, description: 'Compact inline chart' },
  { name: 'Pie Chart', icon: PieChart, description: 'Proportional breakdown' },
];

export default function NewDashboardPage() {
  const { hasAccess } = useTierGate('studio.dashboards.custom');

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <PageHeader title="New Dashboard" description="Build a custom analytical dashboard" />
        <TierGate requiredTier="strategist" featureName="Custom Dashboards" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="New Dashboard"
        description="Drag tiles from the palette to build your dashboard"
        actions={
          <>
            <Button variant="outline" size="sm">
              <Eye className="h-3.5 w-3.5" />
              Preview
            </Button>
            <Button variant="primary" size="sm">
              <Save className="h-3.5 w-3.5" />
              Save
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr]">
        {/* Tile Palette */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Tile Palette</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {tileTypes.map((tile) => {
                const Icon = tile.icon;
                return (
                  <div
                    key={tile.name}
                    className="flex cursor-grab items-center gap-2.5 rounded-md border border-[var(--border-default)] p-2 text-sm transition-colors hover:bg-[var(--surface-2)]"
                  >
                    <GripVertical className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                    <Icon className="h-3.5 w-3.5 text-[var(--accent-500)]" />
                    <div>
                      <p className="text-xs font-medium text-[var(--text-primary)]">{tile.name}</p>
                      <p className="text-[10px] text-[var(--text-tertiary)]">{tile.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Grid Canvas */}
        <Card>
          <CardContent className="p-4">
            <div className="flex h-[480px] items-center justify-center rounded-md border-2 border-dashed border-[var(--border-default)] bg-[var(--surface-0)] text-sm text-[var(--text-tertiary)]">
              Drag tiles from the palette to build your dashboard
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
