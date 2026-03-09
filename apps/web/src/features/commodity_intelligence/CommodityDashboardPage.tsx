import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import PriceDisplay from '@/shared_ui_components/PriceDisplay';
import LoadingSpinner from '@/shared_ui_components/LoadingSpinner';
import { fetchCommodities, type CommodityPrice } from '@/api_client/commodity_api_client';

const mockCommodities: CommodityPrice[] = [
  { symbol: 'CPO', name: 'Crude Palm Oil', price: 3842, change: 28, change_pct: 0.73, unit: 'MYR/MT', source: 'MDEX' },
  { symbol: 'COAL', name: 'Newcastle Coal', price: 128.5, change: -2.3, change_pct: -1.76, unit: 'USD/MT', source: 'ICE' },
  { symbol: 'NICKEL', name: 'Nickel', price: 16250, change: 185, change_pct: 1.15, unit: 'USD/MT', source: 'LME' },
  { symbol: 'ICP', name: 'Indonesia Crude Price', price: 78.4, change: -0.8, change_pct: -1.01, unit: 'USD/bbl', source: 'ESDM' },
  { symbol: 'TIN', name: 'Tin', price: 28500, change: 320, change_pct: 1.14, unit: 'USD/MT', source: 'LME' },
  { symbol: 'GOLD', name: 'Gold', price: 2350, change: 12, change_pct: 0.51, unit: 'USD/oz', source: 'COMEX' },
];

export default function CommodityDashboardPage() {
  const navigate = useNavigate();
  const { data: commodities, isLoading } = useQuery({
    queryKey: ['commodities'],
    queryFn: fetchCommodities,
    placeholderData: mockCommodities,
  });

  if (isLoading) return <LoadingSpinner label="Loading commodity prices..." />;

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Indonesia Commodity Intelligence
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {(commodities ?? []).map((c) => (
          <div
            key={c.symbol}
            onClick={() => navigate(`/commodities/${c.symbol}`)}
            className="bg-bloomberg-bg-secondary border border-bloomberg-border rounded-md p-3 hover:border-bloomberg-accent/50 cursor-pointer transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono font-bold text-bloomberg-accent">{c.symbol}</span>
              <span className="text-xxs text-bloomberg-text-muted">{c.source}</span>
            </div>
            <div className="text-xs text-bloomberg-text-muted mb-1 truncate">{c.name}</div>
            <PriceDisplay price={c.price} change={c.change} changePercent={c.change_pct} size="sm" />
            <div className="text-xxs text-bloomberg-text-muted mt-1">{c.unit}</div>
          </div>
        ))}
      </div>

      <DashboardCard title="Indonesia Export Commodities" subtitle="Key correlations">
        <div className="text-xs text-bloomberg-text-secondary space-y-2">
          <div className="flex justify-between py-1 border-b border-bloomberg-border/30">
            <span>CPO &rarr; AALI, LSIP, SIMP</span>
            <span className="font-mono text-bloomberg-green">Corr: 0.82</span>
          </div>
          <div className="flex justify-between py-1 border-b border-bloomberg-border/30">
            <span>Coal &rarr; ADRO, PTBA, ITMG</span>
            <span className="font-mono text-bloomberg-green">Corr: 0.91</span>
          </div>
          <div className="flex justify-between py-1 border-b border-bloomberg-border/30">
            <span>Nickel &rarr; ANTM, INCO, MBMA</span>
            <span className="font-mono text-bloomberg-green">Corr: 0.75</span>
          </div>
          <div className="flex justify-between py-1">
            <span>ICP &rarr; MEDC, ELSA</span>
            <span className="font-mono text-bloomberg-green">Corr: 0.68</span>
          </div>
        </div>
      </DashboardCard>
    </div>
  );
}
