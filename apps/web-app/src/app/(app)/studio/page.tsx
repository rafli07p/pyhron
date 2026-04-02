import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { BarChart3, LayoutDashboard, Search, Sparkles } from 'lucide-react';
import Link from 'next/link';

export const metadata = { title: 'Studio' };

const quickStart = [
  {
    title: 'Workbench',
    description: 'Build custom charts and explore metrics interactively',
    href: '/studio/workbench',
    icon: BarChart3,
  },
  {
    title: 'Dashboards',
    description: 'Create and manage multi-tile analytical dashboards',
    href: '/studio/dashboards',
    icon: LayoutDashboard,
  },
  {
    title: 'Screener',
    description: 'Filter and rank IDX stocks by fundamental and technical criteria',
    href: '/studio/screener',
    icon: Search,
  },
];

const curatedPresets = [
  { name: 'IDX Sector Rotation', description: 'Sector performance heatmap with relative strength', id: 'sector-rotation' },
  { name: 'LQ45 Valuation', description: 'P/E, P/B, and dividend yield across LQ45 constituents', id: 'lq45-valuation' },
  { name: 'Macro Dashboard', description: 'BI rate, inflation, rupiah, and bond yields', id: 'macro-dashboard' },
  { name: 'Momentum Scanner', description: 'Top momentum stocks ranked by 3M return and volume surge', id: 'momentum-scanner' },
];

export default function StudioPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Studio"
        description="Build charts, dashboards, and screeners for the Indonesian market"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {quickStart.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <Card className="group h-full cursor-pointer transition-colors hover:border-[var(--accent-500)]">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="rounded-md bg-[var(--accent-50)] p-2">
                      <Icon className="h-4 w-4 text-[var(--accent-500)]" />
                    </div>
                    <CardTitle className="group-hover:text-[var(--accent-500)]">{item.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[var(--text-secondary)]">{item.description}</p>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Charts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="flex h-32 items-center justify-center rounded-md bg-[var(--surface-2)] text-xs text-[var(--text-tertiary)]"
              >
                No recent chart
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[var(--accent-500)]" />
            Curated Presets
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {curatedPresets.map((preset) => (
              <Link key={preset.id} href={`/studio/workbench/${preset.id}`}>
                <div className="rounded-md border border-[var(--border-default)] p-3 transition-colors hover:bg-[var(--surface-2)]">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{preset.name}</p>
                  <p className="mt-1 text-xs text-[var(--text-tertiary)]">{preset.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
