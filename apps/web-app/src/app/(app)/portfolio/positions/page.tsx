import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

export const metadata = { title: 'Positions' };

export default function PositionsPage() {
  const positions = [
    { symbol: 'BBCA', name: 'Bank Central Asia', lots: 50, avgPrice: 9500, currentPrice: 9875, pnl: 1875000, pnlPct: 3.95, weight: 35.2 },
    { symbol: 'BMRI', name: 'Bank Mandiri', lots: 80, avgPrice: 6100, currentPrice: 6225, pnl: 1000000, pnlPct: 2.05, weight: 28.1 },
    { symbol: 'TLKM', name: 'Telkom Indonesia', lots: 120, avgPrice: 3900, currentPrice: 3850, pnl: -600000, pnlPct: -1.28, weight: 18.5 },
    { symbol: 'ASII', name: 'Astra International', lots: 40, avgPrice: 4800, currentPrice: 4750, pnl: -200000, pnlPct: -1.04, weight: 10.2 },
    { symbol: 'BBRI', name: 'Bank Rakyat Indonesia', lots: 30, avgPrice: 5400, currentPrice: 5550, pnl: 450000, pnlPct: 2.78, weight: 8.0 },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Positions" description="Current positions with real-time P&L" />
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  {['Symbol', 'Lots', 'Avg Price', 'Current', 'P&L', 'P&L %', 'Weight'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-default)]">
                {positions.map((p) => (
                  <tr key={p.symbol} className="hover:bg-[var(--surface-3)]">
                    <td className="px-4 py-3">
                      <span className="font-medium text-[var(--text-primary)]">{p.symbol}</span>
                      <span className="ml-2 text-xs text-[var(--text-tertiary)]">{p.name}</span>
                    </td>
                    <td className="tabular-nums px-4 py-3 text-[var(--text-secondary)]">{p.lots}</td>
                    <td className="tabular-nums px-4 py-3 text-[var(--text-secondary)]">{p.avgPrice.toLocaleString('id-ID')}</td>
                    <td className="tabular-nums px-4 py-3 font-medium text-[var(--text-primary)]">{p.currentPrice.toLocaleString('id-ID')}</td>
                    <td className={`tabular-nums px-4 py-3 font-medium ${p.pnl > 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                      {p.pnl > 0 ? '+' : ''}{p.pnl.toLocaleString('id-ID')}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={p.pnlPct > 0 ? 'positive' : 'negative'}>
                        {p.pnlPct > 0 ? '+' : ''}{p.pnlPct.toFixed(2)}%
                      </Badge>
                    </td>
                    <td className="tabular-nums px-4 py-3 text-[var(--text-secondary)]">{p.weight.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
