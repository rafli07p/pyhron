import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import Link from 'next/link';

export const metadata = { title: 'Markets' };

function MarketStatus() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-[var(--positive)]" />
        <span className="text-sm font-medium text-[var(--positive)]">Market Open</span>
      </span>
      <span className="text-sm text-[var(--text-tertiary)]">Session II — Closes 15:00 WIB</span>
    </div>
  );
}

function IndexCard({ name, value, change, changePercent }: { name: string; value: string; change: string; changePercent: number }) {
  const isPositive = changePercent > 0;
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">{name}</p>
      <p className="mt-1 tabular-nums text-xl font-semibold text-[var(--text-primary)]">{value}</p>
      <p className={`tabular-nums text-sm font-medium ${isPositive ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
        {isPositive ? '+' : ''}{change} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
      </p>
    </Card>
  );
}

function SectorHeatmap() {
  const sectors = [
    { name: 'Financials', change: 1.2, weight: 35 },
    { name: 'Consumer', change: -0.5, weight: 15 },
    { name: 'Energy', change: 2.1, weight: 12 },
    { name: 'Industrials', change: 0.3, weight: 10 },
    { name: 'Technology', change: -1.8, weight: 8 },
    { name: 'Healthcare', change: 0.7, weight: 7 },
    { name: 'Materials', change: -0.2, weight: 6 },
    { name: 'Infra', change: 1.5, weight: 4 },
    { name: 'Property', change: -0.8, weight: 3 },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sector Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-1">
          {sectors.map((s) => (
            <div
              key={s.name}
              className={`flex flex-col items-center justify-center rounded-md p-3 ${
                s.change > 0 ? 'bg-[var(--positive-muted)]' : 'bg-[var(--negative-muted)]'
              }`}
              style={{ gridColumn: s.weight > 20 ? 'span 2' : undefined }}
            >
              <span className="text-xs font-medium text-[var(--text-primary)]">{s.name}</span>
              <span className={`tabular-nums text-sm font-semibold ${s.change > 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                {s.change > 0 ? '+' : ''}{s.change.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function TopMoversTable() {
  const stocks = [
    { symbol: 'BREN', name: 'Barito Renewables', price: 8250, change: 4.8, volume: '125.3M' },
    { symbol: 'BBCA', name: 'Bank Central Asia', price: 9875, change: 2.3, volume: '45.2M' },
    { symbol: 'GOTO', name: 'GoTo Gojek Tokopedia', price: 82, change: -3.5, volume: '892.1M' },
    { symbol: 'TLKM', name: 'Telkom Indonesia', price: 3850, change: -1.1, volume: '67.8M' },
    { symbol: 'BMRI', name: 'Bank Mandiri', price: 6225, change: 0.8, volume: '34.5M' },
    { symbol: 'ASII', name: 'Astra International', price: 4750, change: -0.5, volume: '28.9M' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Movers</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-default)]">
                <th className="pb-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Symbol</th>
                <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Price</th>
                <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Change</th>
                <th className="hidden pb-2 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)] sm:table-cell">Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-default)]">
              {stocks.map((s) => (
                <tr key={s.symbol} className="hover:bg-[var(--surface-3)]">
                  <td className="py-2">
                    <Link href={`/markets/${s.symbol}`} className="hover:underline">
                      <span className="font-medium text-[var(--text-primary)]">{s.symbol}</span>
                      <span className="ml-2 hidden text-[var(--text-tertiary)] md:inline">{s.name}</span>
                    </Link>
                  </td>
                  <td className="tabular-nums py-2 text-right text-[var(--text-primary)]">
                    {s.price.toLocaleString('id-ID')}
                  </td>
                  <td className={`tabular-nums py-2 text-right font-medium ${s.change > 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'}`}>
                    {s.change > 0 ? '+' : ''}{s.change.toFixed(1)}%
                  </td>
                  <td className="hidden tabular-nums py-2 text-right text-[var(--text-secondary)] sm:table-cell">
                    {s.volume}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export default function MarketsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Markets"
        description="IDX market overview"
        actions={<MarketStatus />}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <IndexCard name="IHSG" value="7.234,56" change="32,45" changePercent={0.45} />
        <IndexCard name="LQ45" value="985,23" change="-5,12" changePercent={-0.52} />
        <IndexCard name="IDX30" value="482,18" change="2,78" changePercent={0.58} />
        <IndexCard name="JII" value="548,92" change="-3,21" changePercent={-0.58} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectorHeatmap />
        <TopMoversTable />
      </div>

      <FinancialDisclaimer className="mt-8" />
    </div>
  );
}
