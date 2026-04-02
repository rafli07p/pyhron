import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import Link from 'next/link';

export const metadata = { title: 'Research' };

export default function ResearchDashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Research Hub" description="Quantitative research and analysis" />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Link href="/research/signals">
          <Card className="p-6 transition-colors hover:border-[var(--accent-500)]">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Signals</h3>
            <p className="mt-1 text-xs text-[var(--text-tertiary)]">ML-generated trading signals with confidence scores</p>
            <p className="mt-3 tabular-nums text-2xl font-bold text-[var(--accent-500)]">12</p>
            <p className="text-xs text-[var(--text-tertiary)]">Active signals</p>
          </Card>
        </Link>
        <Link href="/research/backtests">
          <Card className="p-6 transition-colors hover:border-[var(--accent-500)]">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Backtests</h3>
            <p className="mt-1 text-xs text-[var(--text-tertiary)]">Strategy backtest results and performance metrics</p>
            <p className="mt-3 tabular-nums text-2xl font-bold text-[var(--accent-500)]">28</p>
            <p className="text-xs text-[var(--text-tertiary)]">Completed backtests</p>
          </Card>
        </Link>
        <Link href="/research/factors">
          <Card className="p-6 transition-colors hover:border-[var(--accent-500)]">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Factor Analysis</h3>
              <Badge variant="accent">PRO</Badge>
            </div>
            <p className="mt-1 text-xs text-[var(--text-tertiary)]">Momentum, value, quality, size factor exposure</p>
            <p className="mt-3 tabular-nums text-2xl font-bold text-[var(--accent-500)]">5</p>
            <p className="text-xs text-[var(--text-tertiary)]">Factor models</p>
          </Card>
        </Link>
      </div>

      <Card>
        <CardHeader><CardTitle>Recent Research</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { title: 'IDX Momentum Factor: Q1 2025 Analysis', date: '2025-03-15', tag: 'Factor' },
              { title: 'Banking Sector Pairs Trading Opportunities', date: '2025-03-12', tag: 'Strategy' },
              { title: 'ML Signal Validation: Walk-Forward Results', date: '2025-03-08', tag: 'ML' },
            ].map((item) => (
              <div key={item.title} className="flex items-center justify-between rounded-md px-2 py-2 hover:bg-[var(--surface-3)]">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">{item.date}</p>
                </div>
                <Badge variant="outline">{item.tag}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
