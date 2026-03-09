import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface BacktestMetrics {
  totalReturn: number;
  annualizedReturn: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  calmarRatio: number;
}

export function BacktestResultsPage() {
  const metrics: BacktestMetrics = {
    totalReturn: 45.2,
    annualizedReturn: 18.5,
    sharpeRatio: 1.45,
    sortinoRatio: 2.1,
    maxDrawdown: -12.3,
    winRate: 58.5,
    totalTrades: 342,
    calmarRatio: 1.50,
  };

  const MetricCard = ({ label, value, suffix = '' }: { label: string; value: number; suffix?: string }) => (
    <DashboardCard title={label}>
      <span className="text-2xl font-mono" style={{
        color: value >= 0 ? theme.semantic.positive : theme.semantic.negative
      }}>
        {value > 0 ? '+' : ''}{value.toFixed(2)}{suffix}
      </span>
    </DashboardCard>
  );

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>Backtest Results</h1>
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Return" value={metrics.totalReturn} suffix="%" />
        <MetricCard label="Sharpe Ratio" value={metrics.sharpeRatio} />
        <MetricCard label="Sortino Ratio" value={metrics.sortinoRatio} />
        <MetricCard label="Max Drawdown" value={metrics.maxDrawdown} suffix="%" />
        <MetricCard label="Annualized Return" value={metrics.annualizedReturn} suffix="%" />
        <MetricCard label="Win Rate" value={metrics.winRate} suffix="%" />
        <MetricCard label="Total Trades" value={metrics.totalTrades} />
        <MetricCard label="Calmar Ratio" value={metrics.calmarRatio} />
      </div>
    </div>
  );
}
