import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import LoadingSpinner from '@/shared_ui_components/LoadingSpinner';
import { fetchMacroOverview, type MacroIndicator } from '@/api_client/macro_api_client';

const mockIndicators: MacroIndicator[] = [
  { id: 'gdp', name: 'GDP Growth (YoY)', value: 5.05, previous: 5.17, unit: '%', trend: 'down' },
  { id: 'inflation', name: 'CPI Inflation (YoY)', value: 2.84, previous: 3.05, unit: '%', trend: 'down' },
  { id: 'bi_rate', name: 'BI-Rate', value: 6.00, previous: 6.00, unit: '%', trend: 'flat' },
  { id: 'usdidrt', name: 'USD/IDR', value: 15845, previous: 15720, unit: '', trend: 'up' },
  { id: 'trade_balance', name: 'Trade Balance', value: 3.56, previous: 2.98, unit: 'USD Bn', trend: 'up' },
  { id: 'reserves', name: 'FX Reserves', value: 145.2, previous: 144.0, unit: 'USD Bn', trend: 'up' },
  { id: 'pmi', name: 'Manufacturing PMI', value: 52.1, previous: 51.7, unit: '', trend: 'up' },
  { id: 'ca_deficit', name: 'Current Account', value: -0.8, previous: -1.2, unit: '% GDP', trend: 'up' },
];

function TrendArrow({ trend }: { trend: string }) {
  if (trend === 'up') return <span className="text-bloomberg-green">{'\u25B2'}</span>;
  if (trend === 'down') return <span className="text-bloomberg-red">{'\u25BC'}</span>;
  return <span className="text-bloomberg-text-muted">{'\u25AC'}</span>;
}

export default function MacroDashboardPage() {
  const navigate = useNavigate();
  const { data: indicators, isLoading } = useQuery({
    queryKey: ['macro-overview'],
    queryFn: fetchMacroOverview,
    placeholderData: mockIndicators,
  });

  if (isLoading) return <LoadingSpinner label="Loading macro data..." />;

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Indonesia Macro Intelligence
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {(indicators ?? []).map((ind) => (
          <div
            key={ind.id}
            onClick={() => navigate(`/macro/indicator/${ind.id}`)}
            className="bg-bloomberg-bg-secondary border border-bloomberg-border rounded-md p-3 hover:border-bloomberg-border-hover cursor-pointer transition-colors"
          >
            <div className="text-xxs text-bloomberg-text-muted uppercase tracking-wider mb-1">
              {ind.name}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-mono font-bold tabular-nums text-bloomberg-text-primary">
                {typeof ind.value === 'number' && ind.value > 1000
                  ? ind.value.toLocaleString()
                  : ind.value}
              </span>
              <span className="text-xxs text-bloomberg-text-muted">{ind.unit}</span>
            </div>
            <div className="flex items-center gap-1 mt-1 text-xs font-mono">
              <TrendArrow trend={ind.trend} />
              <span className="text-bloomberg-text-muted tabular-nums">
                prev: {ind.previous}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
