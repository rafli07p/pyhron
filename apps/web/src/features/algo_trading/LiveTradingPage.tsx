import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { PriceDisplay } from '../../shared_ui_components/PriceDisplay';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface Position {
  symbol: string;
  quantity: number;
  avgEntry: number;
  currentPrice: number;
  unrealizedPnl: number;
}

interface Order {
  clientOrderId: string;
  symbol: string;
  side: string;
  quantity: number;
  status: string;
  createdAt: string;
}

export function LiveTradingPage() {
  const positions: Position[] = [
    { symbol: 'BBCA', quantity: 5000, avgEntry: 9250, currentPrice: 9475, unrealizedPnl: 1125000 },
    { symbol: 'TLKM', quantity: 10000, avgEntry: 3850, currentPrice: 3780, unrealizedPnl: -700000 },
    { symbol: 'ADRO', quantity: 8000, avgEntry: 2650, currentPrice: 2720, unrealizedPnl: 560000 },
  ];

  const orders: Order[] = [
    { clientOrderId: 'ORD-001', symbol: 'ASII', side: 'BUY', quantity: 3000, status: 'FILLED', createdAt: '09:15:32' },
    { clientOrderId: 'ORD-002', symbol: 'BMRI', side: 'SELL', quantity: 2000, status: 'SUBMITTED', createdAt: '09:22:15' },
  ];

  const formatIDR = (v: number) => new Intl.NumberFormat('id-ID').format(v);

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>Live Trading</h1>

      <DashboardCard title="Open Positions">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr style={{ color: theme.text.secondary }}>
              <th className="text-left py-1">Symbol</th>
              <th className="text-right py-1">Qty</th>
              <th className="text-right py-1">Avg Entry</th>
              <th className="text-right py-1">Current</th>
              <th className="text-right py-1">Unrealized P&L</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.symbol} className="border-t" style={{ borderColor: theme.bg.tertiary }}>
                <td className="py-1" style={{ color: theme.accent.primary }}>{p.symbol}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>{formatIDR(p.quantity)}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>{formatIDR(p.avgEntry)}</td>
                <td className="text-right py-1"><PriceDisplay price={p.currentPrice} change={p.currentPrice - p.avgEntry} /></td>
                <td className="text-right py-1" style={{ color: p.unrealizedPnl >= 0 ? theme.semantic.positive : theme.semantic.negative }}>
                  {p.unrealizedPnl >= 0 ? '+' : ''}{formatIDR(p.unrealizedPnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DashboardCard>

      <DashboardCard title="Recent Orders">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr style={{ color: theme.text.secondary }}>
              <th className="text-left py-1">ID</th>
              <th className="text-left py-1">Symbol</th>
              <th className="text-left py-1">Side</th>
              <th className="text-right py-1">Qty</th>
              <th className="text-right py-1">Status</th>
              <th className="text-right py-1">Time</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.clientOrderId} className="border-t" style={{ borderColor: theme.bg.tertiary }}>
                <td className="py-1" style={{ color: theme.text.secondary }}>{o.clientOrderId}</td>
                <td className="py-1" style={{ color: theme.accent.primary }}>{o.symbol}</td>
                <td className="py-1" style={{ color: o.side === 'BUY' ? theme.semantic.positive : theme.semantic.negative }}>{o.side}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>{formatIDR(o.quantity)}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>{o.status}</td>
                <td className="text-right py-1" style={{ color: theme.text.secondary }}>{o.createdAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DashboardCard>
    </div>
  );
}
