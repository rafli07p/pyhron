'use client';

const mockStrategies = [
  { id: 'strat-001', name: 'IDX Momentum', type: 'momentum', enabled: true, returnPct: 15.2, sharpe: 0.82, drawdown: -8.5, trades: 48, description: '12-1 month momentum on LQ45' },
  { id: 'strat-002', name: 'Value-Quality', type: 'value', enabled: true, returnPct: 11.8, sharpe: 0.65, drawdown: -12.1, trades: 24, description: 'Value + quality factor composite' },
  { id: 'strat-003', name: 'Pairs Banking', type: 'pairs', enabled: false, returnPct: 8.4, sharpe: 1.52, drawdown: -3.2, trades: 156, description: 'BBCA-BBRI cointegration pairs' },
];

export function StrategiesList() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {mockStrategies.map((strategy) => (
        <div key={strategy.id} className="rounded-lg border border-border bg-bg-secondary p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-text-primary">{strategy.name}</h3>
            <div className={`rounded-full px-2 py-0.5 text-xs ${strategy.enabled ? 'bg-positive/10 text-positive' : 'bg-bg-tertiary text-text-muted'}`}>
              {strategy.enabled ? 'Active' : 'Disabled'}
            </div>
          </div>
          <p className="text-xs text-text-muted mb-4">{strategy.description}</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-text-muted">Return</p>
              <p className={`font-mono ${strategy.returnPct >= 0 ? 'text-positive' : 'text-negative'}`}>
                {strategy.returnPct >= 0 ? '+' : ''}{strategy.returnPct}%
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Sharpe</p>
              <p className="font-mono text-text-primary">{strategy.sharpe}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Max DD</p>
              <p className="font-mono text-negative">{strategy.drawdown}%</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Trades</p>
              <p className="font-mono text-text-primary">{strategy.trades}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
