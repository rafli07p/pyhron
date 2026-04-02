import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';
import Link from 'next/link';

export const metadata = { title: 'Orders' };

export default function OrdersPage() {
  const orders = [
    { id: '1', symbol: 'BBCA', side: 'buy', type: 'limit', qty: 500, price: 9850, status: 'new', time: '14:32:05' },
    { id: '2', symbol: 'BMRI', side: 'buy', type: 'limit', qty: 300, price: 6200, status: 'partially_filled', time: '14:28:12' },
    { id: '3', symbol: 'TLKM', side: 'sell', type: 'market', qty: 1000, price: null, status: 'filled', time: '14:15:30' },
    { id: '4', symbol: 'ASII', side: 'buy', type: 'limit', qty: 200, price: 4700, status: 'cancelled', time: '13:45:00' },
  ];

  const statusVariant: Record<string, 'info' | 'warning' | 'positive' | 'default'> = {
    new: 'info', partially_filled: 'warning', filled: 'positive', cancelled: 'default',
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="Order management"
        actions={<Button size="sm" asChild><Link href="/portfolio/orders/new">New Order</Link></Button>}
      />
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  {['Time', 'Symbol', 'Side', 'Type', 'Qty', 'Price', 'Status'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-default)]">
                {orders.map((o) => (
                  <tr key={o.id} className="hover:bg-[var(--surface-3)]">
                    <td className="tabular-nums px-4 py-3 text-[var(--text-tertiary)]">{o.time}</td>
                    <td className="px-4 py-3 font-medium text-[var(--text-primary)]">{o.symbol}</td>
                    <td className="px-4 py-3"><Badge variant={o.side === 'buy' ? 'positive' : 'negative'}>{o.side}</Badge></td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{o.type}</td>
                    <td className="tabular-nums px-4 py-3 text-[var(--text-secondary)]">{o.qty}</td>
                    <td className="tabular-nums px-4 py-3 text-[var(--text-secondary)]">{o.price?.toLocaleString('id-ID') ?? '—'}</td>
                    <td className="px-4 py-3"><Badge variant={statusVariant[o.status] ?? 'default'}>{o.status.replace('_', ' ')}</Badge></td>
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
