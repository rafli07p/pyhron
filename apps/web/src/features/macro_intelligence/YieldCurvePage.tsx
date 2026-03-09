import DashboardCard from '@/shared_ui_components/DashboardCard';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { themeTokens } from '@/design_system/bloomberg_dark_theme_tokens';

interface YieldPoint {
  tenor: string;
  current: number;
  month_ago: number;
  year_ago: number;
}

const yieldData: YieldPoint[] = [
  { tenor: '1M', current: 5.85, month_ago: 5.80, year_ago: 5.50 },
  { tenor: '3M', current: 6.02, month_ago: 5.95, year_ago: 5.65 },
  { tenor: '6M', current: 6.15, month_ago: 6.08, year_ago: 5.78 },
  { tenor: '1Y', current: 6.32, month_ago: 6.25, year_ago: 5.95 },
  { tenor: '2Y', current: 6.48, month_ago: 6.40, year_ago: 6.10 },
  { tenor: '5Y', current: 6.72, month_ago: 6.65, year_ago: 6.35 },
  { tenor: '10Y', current: 6.95, month_ago: 6.88, year_ago: 6.60 },
  { tenor: '15Y', current: 7.08, month_ago: 7.00, year_ago: 6.75 },
  { tenor: '20Y', current: 7.15, month_ago: 7.08, year_ago: 6.82 },
  { tenor: '30Y', current: 7.18, month_ago: 7.12, year_ago: 6.88 },
];

export default function YieldCurvePage() {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Indonesia Government Bond Yield Curve
      </h2>

      <DashboardCard title="SBN Yield Curve" subtitle="IDR Government Bonds">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={yieldData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={themeTokens.colors.border.default} />
              <XAxis dataKey="tenor" tick={{ fill: themeTokens.colors.text.secondary, fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: themeTokens.colors.text.secondary, fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: themeTokens.colors.bg.elevated, border: `1px solid ${themeTokens.colors.border.default}`, color: themeTokens.colors.text.primary, fontSize: 11, fontFamily: 'monospace' }} />
              <Line type="monotone" dataKey="current" stroke={themeTokens.colors.accent.orange} strokeWidth={2} dot={{ r: 3 }} name="Current" />
              <Line type="monotone" dataKey="month_ago" stroke={themeTokens.colors.text.secondary} strokeWidth={1} strokeDasharray="4 4" dot={false} name="1M Ago" />
              <Line type="monotone" dataKey="year_ago" stroke={themeTokens.colors.text.muted} strokeWidth={1} strokeDasharray="2 2" dot={false} name="1Y Ago" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </DashboardCard>

      <DashboardCard title="Spread Analysis" dense>
        <div className="grid grid-cols-3 gap-4 text-xs font-mono">
          <div>
            <div className="text-bloomberg-text-muted text-xxs">2Y-10Y Spread</div>
            <div className="text-bloomberg-text-primary font-semibold">47 bps</div>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs">10Y vs UST</div>
            <div className="text-bloomberg-text-primary font-semibold">265 bps</div>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs">Curve Shape</div>
            <div className="text-bloomberg-green font-semibold">Normal</div>
          </div>
        </div>
      </DashboardCard>
    </div>
  );
}
