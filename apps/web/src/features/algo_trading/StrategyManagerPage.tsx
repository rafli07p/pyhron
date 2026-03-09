import { useState } from 'react';
import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface Strategy {
  id: string;
  name: string;
  type: string;
  isEnabled: boolean;
  pnlToday: number;
  sharpe: number;
}

export function StrategyManagerPage() {
  const [strategies] = useState<Strategy[]>([
    { id: '1', name: 'IDX Momentum Cross-Section', type: 'momentum', isEnabled: true, pnlToday: 2500000, sharpe: 1.45 },
    { id: '2', name: 'Bollinger Mean Reversion', type: 'mean_reversion', isEnabled: true, pnlToday: -800000, sharpe: 0.92 },
    { id: '3', name: 'Pairs Cointegration BBCA-BMRI', type: 'pairs', isEnabled: false, pnlToday: 0, sharpe: 1.12 },
  ]);

  const formatIDR = (v: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(v);

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>Strategy Manager</h1>
        <button className="px-4 py-2 rounded text-sm font-bold" style={{ backgroundColor: theme.accent.primary, color: '#000' }}>
          + New Strategy
        </button>
      </div>
      <div className="space-y-2">
        {strategies.map((s) => (
          <DashboardCard key={s.id} title={s.name}>
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <span className="text-xs px-2 py-1 rounded" style={{
                  backgroundColor: s.isEnabled ? theme.semantic.positive + '33' : theme.bg.tertiary,
                  color: s.isEnabled ? theme.semantic.positive : theme.text.secondary,
                }}>
                  {s.isEnabled ? 'LIVE' : 'DISABLED'}
                </span>
                <span className="text-sm" style={{ color: theme.text.secondary }}>{s.type}</span>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <div className="text-xs" style={{ color: theme.text.secondary }}>Today P&L</div>
                  <div className="font-mono" style={{ color: s.pnlToday >= 0 ? theme.semantic.positive : theme.semantic.negative }}>
                    {formatIDR(s.pnlToday)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs" style={{ color: theme.text.secondary }}>Sharpe</div>
                  <div className="font-mono" style={{ color: theme.text.primary }}>{s.sharpe.toFixed(2)}</div>
                </div>
              </div>
            </div>
          </DashboardCard>
        ))}
      </div>
    </div>
  );
}
