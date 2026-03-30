import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Portfolio' };

export default function PortfolioPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-medium text-text-primary">Portfolio</h1>
      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">Factor Exposure</h3>
        <div className="h-[300px] flex items-center justify-center text-text-muted">
          Factor exposure bar chart placeholder (Recharts)
        </div>
      </div>
      <div className="rounded-lg border border-border bg-bg-secondary p-6">
        <h3 className="text-sm font-medium text-text-muted mb-4">Positions</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left text-text-muted">Symbol</th>
                <th className="py-2 text-right text-text-muted">Qty</th>
                <th className="py-2 text-right text-text-muted">Avg Cost</th>
                <th className="py-2 text-right text-text-muted">Current</th>
                <th className="py-2 text-right text-text-muted">P&L</th>
                <th className="py-2 text-right text-text-muted">Weight</th>
              </tr>
            </thead>
            <tbody>
              {[
                { symbol: 'BBCA', qty: 500, avgCost: 9500, current: 9875, pnl: 187500, weight: 8.5 },
                { symbol: 'BBRI', qty: 800, avgCost: 5400, current: 5525, pnl: 100000, weight: 7.2 },
                { symbol: 'TLKM', qty: 1200, avgCost: 3900, current: 3840, pnl: -72000, weight: 6.8 },
                { symbol: 'ADRO', qty: 600, avgCost: 3500, current: 3750, pnl: 150000, weight: 4.5 },
              ].map((pos) => (
                <tr key={pos.symbol} className="border-b border-border last:border-0">
                  <td className="py-2 font-mono font-medium">{pos.symbol}</td>
                  <td className="py-2 text-right font-mono">{pos.qty}</td>
                  <td className="py-2 text-right font-mono">{pos.avgCost.toLocaleString('id-ID')}</td>
                  <td className="py-2 text-right font-mono">{pos.current.toLocaleString('id-ID')}</td>
                  <td className={`py-2 text-right font-mono ${pos.pnl >= 0 ? 'text-positive' : 'text-negative'}`}>
                    {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toLocaleString('id-ID')}
                  </td>
                  <td className="py-2 text-right font-mono">{pos.weight}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
