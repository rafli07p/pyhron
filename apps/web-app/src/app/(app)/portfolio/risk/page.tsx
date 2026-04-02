import { PageHeader } from '@/design-system/layout/PageHeader';
import { StatCard } from '@/design-system/data-display/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import { Shield, TrendingDown, BarChart3, Activity } from 'lucide-react';

export const metadata = { title: 'Risk Dashboard' };

export default function RiskPage() {
  const stressScenarios = [
    { name: '2020 COVID', impact: -18.4, varChange: 340 },
    { name: '2013 Taper Tantrum', impact: -12.1, varChange: 180 },
    { name: 'IDR -10%', impact: -8.7, varChange: 120 },
    { name: 'Rates +200bps', impact: -5.3, varChange: 80 },
    { name: 'Oil +50%', impact: -2.1, varChange: 30 },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Risk Dashboard" description="Portfolio risk analytics" />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="VaR (95%, 1d)" value="-IDR 45.2M" delta="-1.2%" deltaType="negative" icon={Shield} />
        <StatCard label="CVaR (95%)" value="-IDR 67.8M" delta="-1.8%" deltaType="negative" icon={TrendingDown} />
        <StatCard label="Max Drawdown" value="-12.3%" delta="23 days" deltaType="negative" icon={BarChart3} />
        <StatCard label="Sharpe (ann.)" value="1.84" delta="Sortino: 2.41" deltaType="neutral" subtitle="Calmar: 1.92" icon={Activity} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Sector Exposure</CardTitle></CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
              D3 treemap loads here
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Correlation Matrix</CardTitle></CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
              D3 correlation heatmap loads here
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Drawdown History</CardTitle></CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center rounded-md bg-[var(--surface-2)] text-sm text-[var(--text-tertiary)]">
              Underwater equity chart loads here
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Stress Scenarios</CardTitle></CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="pb-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Scenario</th>
                  <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Impact</th>
                  <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">VaR Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-default)]">
                {stressScenarios.map((s) => (
                  <tr key={s.name}>
                    <td className="py-2 text-[var(--text-primary)]">{s.name}</td>
                    <td className="tabular-nums py-2 text-right font-medium text-[var(--negative)]">{s.impact}%</td>
                    <td className="tabular-nums py-2 text-right text-[var(--warning)]">+{s.varChange}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
