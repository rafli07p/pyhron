import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';

export const metadata = { title: 'Trade History' };

const MOCK_TRADES = [
  { id: '1', date: '2025-03-15 14:32', symbol: 'BBCA', side: 'buy', quantity: 500, price: 9875, commission: 7406, pnl: null },
  { id: '2', date: '2025-03-15 10:15', symbol: 'TLKM', side: 'sell', quantity: 1000, price: 3780, commission: 9450, pnl: 234500 },
  { id: '3', date: '2025-03-14 13:45', symbol: 'BMRI', side: 'buy', quantity: 800, price: 5450, commission: 6540, pnl: null },
  { id: '4', date: '2025-03-14 09:30', symbol: 'ASII', side: 'sell', quantity: 300, price: 4650, commission: 3488, pnl: -87500 },
  { id: '5', date: '2025-03-13 14:50', symbol: 'UNVR', side: 'buy', quantity: 200, price: 3890, commission: 1167, pnl: null },
  { id: '6', date: '2025-03-13 10:20', symbol: 'BBRI', side: 'sell', quantity: 600, price: 5125, commission: 7688, pnl: 456000 },
  { id: '7', date: '2025-03-12 13:15', symbol: 'MDKA', side: 'buy', quantity: 1000, price: 2340, commission: 3510, pnl: null },
  { id: '8', date: '2025-03-12 09:05', symbol: 'BBCA', side: 'sell', quantity: 300, price: 9800, commission: 7350, pnl: 312000 },
];

function formatIDR(value: number) {
  return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(value);
}

export default function TradeHistoryPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Trade History" description="Complete trade execution history" />

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-tertiary)]">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-tertiary)]">Symbol</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-tertiary)]">Side</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-tertiary)]">Qty</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-tertiary)]">Price</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-tertiary)]">Commission</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-tertiary)]">P&L</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_TRADES.map((trade) => (
                  <tr key={trade.id} className="border-b border-[var(--border-default)] hover:bg-[var(--surface-2)]">
                    <td className="px-4 py-3 text-xs tabular-nums text-[var(--text-secondary)]">{trade.date}</td>
                    <td className="px-4 py-3 text-xs font-medium text-[var(--text-primary)]">{trade.symbol}</td>
                    <td className="px-4 py-3">
                      <Badge variant={trade.side === 'buy' ? 'positive' : 'negative'}>
                        {trade.side.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-secondary)]">{formatIDR(trade.quantity)}</td>
                    <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-secondary)]">{formatIDR(trade.price)}</td>
                    <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-tertiary)]">{formatIDR(trade.commission)}</td>
                    <td className={`px-4 py-3 text-right text-xs tabular-nums font-medium ${
                      trade.pnl === null ? 'text-[var(--text-tertiary)]'
                      : trade.pnl >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'
                    }`}>
                      {trade.pnl === null ? '\u2014' : `${trade.pnl >= 0 ? '+' : ''}${formatIDR(trade.pnl)}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
