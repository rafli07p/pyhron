import { PageHeader } from '@/design-system/layout/PageHeader';
import { StatCard } from '@/design-system/data-display/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

export const metadata = { title: 'Performance' };

export default function PerformancePage() {
  return (
    <div className="space-y-3">
      <PageHeader title="Performance Attribution" description="Portfolio performance analysis and attribution" />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total Return (YTD)"
          value="+23.45%"
          delta="+8.2% vs IHSG"
          deltaType="positive"
        />
        <StatCard
          label="CAGR (Since Inception)"
          value="+18.7%"
          delta="Since Jan 2024"
          deltaType="positive"
        />
        <StatCard
          label="Information Ratio"
          value="1.42"
          delta="vs IHSG"
          deltaType="positive"
        />
        <StatCard
          label="Tracking Error"
          value="8.3%"
          delta="Annualized"
          deltaType="neutral"
        />
      </div>

      {/* Equity Curve Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve vs Benchmark</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center">
            <Skeleton className="h-full w-full rounded-md" />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Monthly Returns */}
        <Card>
          <CardHeader>
            <CardTitle>Monthly Returns</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-12 gap-1">
              {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((month) => (
                <div key={month} className="text-center text-[10px] text-[var(--text-tertiary)]">
                  {month}
                </div>
              ))}
              {[2.1, -0.8, 3.4, 1.2, -1.5, 2.8, 0.3, 4.1, -2.3, 1.7, 3.2, 0.9].map((ret, i) => (
                <div
                  key={i}
                  className={`flex h-8 items-center justify-center rounded text-[10px] font-medium tabular-nums ${
                    ret > 0
                      ? 'bg-[var(--positive-muted)] text-[var(--positive)]'
                      : 'bg-[var(--negative-muted)] text-[var(--negative)]'
                  }`}
                >
                  {ret > 0 ? '+' : ''}{ret.toFixed(1)}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Sector Attribution */}
        <Card>
          <CardHeader>
            <CardTitle>Sector Attribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {[
                { sector: 'Financials', allocation: 35, selection: 2.1, total: 3.8 },
                { sector: 'Consumer', allocation: 20, selection: -0.5, total: 0.8 },
                { sector: 'Technology', allocation: 15, selection: 1.8, total: 2.4 },
                { sector: 'Basic Materials', allocation: 12, selection: 0.3, total: 0.6 },
                { sector: 'Industrials', allocation: 10, selection: -0.2, total: 0.1 },
                { sector: 'Others', allocation: 8, selection: 0.1, total: 0.2 },
              ].map((row) => (
                <div key={row.sector} className="flex items-center justify-between text-xs">
                  <span className="w-28 text-[var(--text-primary)]">{row.sector}</span>
                  <span className="w-12 text-right tabular-nums text-[var(--text-tertiary)]">{row.allocation}%</span>
                  <span className={`w-16 text-right tabular-nums ${row.selection >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                    {row.selection >= 0 ? '+' : ''}{row.selection.toFixed(1)}%
                  </span>
                  <span className={`w-16 text-right tabular-nums font-medium ${row.total >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                    {row.total >= 0 ? '+' : ''}{row.total.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
