import { useState } from 'react';
import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface YieldPoint {
  tenor: string;
  tenorMonths: number;
  yieldPct: number;
  changeBps: number;
}

export default function YieldCurveAnalysisPage() {
  const [curveDate, setCurveDate] = useState(new Date().toISOString().split('T')[0]);
  const [yieldData] = useState<YieldPoint[]>([
    { tenor: '3M', tenorMonths: 3, yieldPct: 5.25, changeBps: -2 },
    { tenor: '1Y', tenorMonths: 12, yieldPct: 5.75, changeBps: 1 },
    { tenor: '2Y', tenorMonths: 24, yieldPct: 6.10, changeBps: 3 },
    { tenor: '5Y', tenorMonths: 60, yieldPct: 6.45, changeBps: -1 },
    { tenor: '10Y', tenorMonths: 120, yieldPct: 6.80, changeBps: 2 },
    { tenor: '20Y', tenorMonths: 240, yieldPct: 7.05, changeBps: 0 },
    { tenor: '30Y', tenorMonths: 360, yieldPct: 7.15, changeBps: -1 },
  ]);

  const slope10y2y = (yieldData.find(y => y.tenorMonths === 120)?.yieldPct ?? 0) -
    (yieldData.find(y => y.tenorMonths === 24)?.yieldPct ?? 0);

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>
          SBN Yield Curve Analysis
        </h1>
        <input
          type="date"
          value={curveDate}
          onChange={(e) => setCurveDate(e.target.value)}
          className="px-3 py-1 rounded text-sm"
          style={{ backgroundColor: theme.bg.tertiary, color: theme.text.primary }}
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <DashboardCard title="10Y-2Y Slope">
          <span className="text-2xl font-mono" style={{
            color: slope10y2y >= 0 ? theme.semantic.positive : theme.semantic.negative
          }}>
            {slope10y2y.toFixed(2)}%
          </span>
        </DashboardCard>
        <DashboardCard title="10Y Benchmark">
          <span className="text-2xl font-mono" style={{ color: theme.text.primary }}>
            {yieldData.find(y => y.tenorMonths === 120)?.yieldPct.toFixed(2)}%
          </span>
        </DashboardCard>
        <DashboardCard title="Curve Shape">
          <span className="text-lg" style={{ color: slope10y2y >= 0 ? theme.semantic.positive : theme.semantic.negative }}>
            {slope10y2y >= 0 ? 'Normal' : 'Inverted'}
          </span>
        </DashboardCard>
      </div>

      <DashboardCard title="Yield Curve Points">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr style={{ color: theme.text.secondary }}>
              <th className="text-left py-1">Tenor</th>
              <th className="text-right py-1">Yield (%)</th>
              <th className="text-right py-1">Change (bps)</th>
            </tr>
          </thead>
          <tbody>
            {yieldData.map((point) => (
              <tr key={point.tenor} className="border-t" style={{ borderColor: theme.bg.tertiary }}>
                <td className="py-1" style={{ color: theme.text.primary }}>{point.tenor}</td>
                <td className="text-right py-1" style={{ color: theme.text.primary }}>
                  {point.yieldPct.toFixed(2)}
                </td>
                <td className="text-right py-1" style={{
                  color: point.changeBps > 0 ? theme.semantic.negative : point.changeBps < 0 ? theme.semantic.positive : theme.text.secondary
                }}>
                  {point.changeBps > 0 ? '+' : ''}{point.changeBps}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DashboardCard>
    </div>
  );
}
