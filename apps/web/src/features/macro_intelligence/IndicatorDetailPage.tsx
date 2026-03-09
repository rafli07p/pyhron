import { useParams, useNavigate } from 'react-router-dom';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { themeTokens } from '@/design_system/bloomberg_dark_theme_tokens';

interface HistoricalPoint {
  date: string;
  value: number;
}

const mockHistory: HistoricalPoint[] = [
  { date: '2024-Q1', value: 5.11 },
  { date: '2024-Q2', value: 5.05 },
  { date: '2024-Q3', value: 4.95 },
  { date: '2024-Q4', value: 5.17 },
  { date: '2025-Q1', value: 5.05 },
  { date: '2025-Q2', value: 5.12 },
  { date: '2025-Q3', value: 4.98 },
  { date: '2025-Q4', value: 5.08 },
];

const indicatorMeta: Record<string, { name: string; unit: string; description: string }> = {
  gdp: { name: 'GDP Growth (YoY)', unit: '%', description: 'Quarterly GDP growth rate year-over-year' },
  inflation: { name: 'CPI Inflation (YoY)', unit: '%', description: 'Consumer Price Index annual change' },
  bi_rate: { name: 'BI-Rate', unit: '%', description: 'Bank Indonesia benchmark interest rate' },
  usdidrt: { name: 'USD/IDR Exchange Rate', unit: 'IDR', description: 'US Dollar to Indonesian Rupiah' },
  trade_balance: { name: 'Trade Balance', unit: 'USD Bn', description: 'Monthly trade balance surplus/deficit' },
  reserves: { name: 'Foreign Exchange Reserves', unit: 'USD Bn', description: 'Bank Indonesia FX reserves' },
  pmi: { name: 'Manufacturing PMI', unit: 'Index', description: 'Purchasing Managers Index for manufacturing' },
  ca_deficit: { name: 'Current Account Balance', unit: '% GDP', description: 'Current account as percentage of GDP' },
};

export default function IndicatorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const meta = indicatorMeta[id ?? ''] ?? { name: id ?? 'Unknown', unit: '', description: '' };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/macro')} className="text-bloomberg-accent text-xs hover:underline">
          &larr; Macro Dashboard
        </button>
        <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">{meta.name}</h2>
      </div>

      <p className="text-xs text-bloomberg-text-secondary">{meta.description}</p>

      <DashboardCard title="Historical Trend" subtitle={meta.unit}>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mockHistory} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={themeTokens.colors.border.default} />
              <XAxis dataKey="date" tick={{ fill: themeTokens.colors.text.secondary, fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: themeTokens.colors.text.secondary, fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: themeTokens.colors.bg.elevated, border: `1px solid ${themeTokens.colors.border.default}`, color: themeTokens.colors.text.primary, fontSize: 11, fontFamily: 'monospace' }} />
              <Line type="monotone" dataKey="value" stroke={themeTokens.colors.accent.orange} strokeWidth={2} dot={{ r: 3, fill: themeTokens.colors.accent.orange }} name={meta.name} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </DashboardCard>

      <DashboardCard title="Statistics" dense>
        <div className="grid grid-cols-4 gap-4 text-xs font-mono">
          <div><div className="text-bloomberg-text-muted text-xxs">Latest</div><div className="font-semibold">5.05{meta.unit && ` ${meta.unit}`}</div></div>
          <div><div className="text-bloomberg-text-muted text-xxs">Average (2Y)</div><div className="font-semibold">5.06</div></div>
          <div><div className="text-bloomberg-text-muted text-xxs">High (2Y)</div><div className="font-semibold">5.17</div></div>
          <div><div className="text-bloomberg-text-muted text-xxs">Low (2Y)</div><div className="font-semibold">4.95</div></div>
        </div>
      </DashboardCard>
    </div>
  );
}
