import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface CreditSpread {
  rating: string;
  spreadBps: number;
  govtYield: number;
  corpYield: number;
  bondCount: number;
}

export function CreditSpreadPage() {
  const spreads: CreditSpread[] = [
    { rating: 'AAA', spreadBps: 45, govtYield: 6.80, corpYield: 7.25, bondCount: 12 },
    { rating: 'AA', spreadBps: 85, govtYield: 6.80, corpYield: 7.65, bondCount: 28 },
    { rating: 'A', spreadBps: 150, govtYield: 6.80, corpYield: 8.30, bondCount: 35 },
    { rating: 'BBB', spreadBps: 280, govtYield: 6.80, corpYield: 9.60, bondCount: 18 },
  ];

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>
        Credit Spread Monitor
      </h1>
      <DashboardCard title="Spreads by Rating (vs 10Y SBN)">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr style={{ color: theme.text.secondary }}>
              <th className="text-left py-1">Rating</th>
              <th className="text-right py-1">Spread (bps)</th>
              <th className="text-right py-1">Corp Yield</th>
              <th className="text-right py-1">Bonds</th>
            </tr>
          </thead>
          <tbody>
            {spreads.map((s) => (
              <tr key={s.rating} className="border-t" style={{ borderColor: theme.bg.tertiary }}>
                <td className="py-1" style={{ color: theme.accent.primary }}>{s.rating}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>{s.spreadBps}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>{s.corpYield.toFixed(2)}%</td>
                <td className="text-right py-1" style={{ color: theme.text.secondary }}>{s.bondCount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DashboardCard>
    </div>
  );
}
