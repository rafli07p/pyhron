import { useParams, useNavigate } from 'react-router-dom';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import PriceDisplay from '@/shared_ui_components/PriceDisplay';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { themeTokens } from '@/design_system/bloomberg_dark_theme_tokens';

const mockPriceHistory = [
  { date: '2025-10', price: 3620 },
  { date: '2025-11', price: 3710 },
  { date: '2025-12', price: 3550 },
  { date: '2026-01', price: 3780 },
  { date: '2026-02', price: 3900 },
  { date: '2026-03', price: 3842 },
];

const commodityMeta: Record<string, { name: string; unit: string; exchange: string }> = {
  CPO: { name: 'Crude Palm Oil', unit: 'MYR/MT', exchange: 'Bursa Malaysia Derivatives' },
  COAL: { name: 'Newcastle Coal', unit: 'USD/MT', exchange: 'ICE Futures' },
  NICKEL: { name: 'Nickel', unit: 'USD/MT', exchange: 'London Metal Exchange' },
  ICP: { name: 'Indonesia Crude Price', unit: 'USD/bbl', exchange: 'ESDM (Ministry)' },
  TIN: { name: 'Tin', unit: 'USD/MT', exchange: 'London Metal Exchange' },
  GOLD: { name: 'Gold', unit: 'USD/oz', exchange: 'COMEX' },
};

export default function CommodityDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const meta = commodityMeta[symbol ?? ''] ?? { name: symbol, unit: '', exchange: '' };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/commodities')} className="text-bloomberg-accent text-xs hover:underline">
          &larr; Commodities
        </button>
        <h2 className="text-sm font-mono font-bold text-bloomberg-accent">{symbol}</h2>
        <span className="text-xs text-bloomberg-text-secondary">{meta.name}</span>
        <span className="text-xxs text-bloomberg-text-muted">{meta.exchange}</span>
      </div>

      <div className="mb-2">
        <PriceDisplay price={3842} change={28} changePercent={0.73} size="lg" />
        <span className="ml-2 text-xs text-bloomberg-text-muted">{meta.unit}</span>
      </div>

      <DashboardCard title="Price History" subtitle="6 Months">
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mockPriceHistory} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={themeTokens.colors.border.default} />
              <XAxis dataKey="date" tick={{ fill: themeTokens.colors.text.secondary, fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: themeTokens.colors.text.secondary, fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: themeTokens.colors.bg.elevated, border: `1px solid ${themeTokens.colors.border.default}`, color: themeTokens.colors.text.primary, fontSize: 11, fontFamily: 'monospace' }} />
              <Line type="monotone" dataKey="price" stroke={themeTokens.colors.accent.orange} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </DashboardCard>

      <DashboardCard title="Key Statistics" dense>
        <div className="grid grid-cols-4 gap-4 text-xs font-mono">
          <div><div className="text-bloomberg-text-muted text-xxs">52W High</div><div className="font-semibold">4,120</div></div>
          <div><div className="text-bloomberg-text-muted text-xxs">52W Low</div><div className="font-semibold">3,280</div></div>
          <div><div className="text-bloomberg-text-muted text-xxs">Avg Volume</div><div className="font-semibold">12.4K lots</div></div>
          <div><div className="text-bloomberg-text-muted text-xxs">YTD Change</div><div className="text-bloomberg-green font-semibold">+8.2%</div></div>
        </div>
      </DashboardCard>
    </div>
  );
}
