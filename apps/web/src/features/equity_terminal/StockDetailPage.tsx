import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import PriceDisplay from '@/shared_ui_components/PriceDisplay';
import LoadingSpinner from '@/shared_ui_components/LoadingSpinner';
import { fetchStockDetail, type StockDetail } from '@/api_client/equity_api_client';

const mockDetail: StockDetail = {
  ticker: 'BBCA',
  name: 'Bank Central Asia Tbk',
  last_price: 9825,
  change: 75,
  change_pct: 0.77,
  open: 9750,
  high: 9850,
  low: 9700,
  volume: 42_300_000,
  market_cap: 1_210_000_000_000_000,
  pe_ratio: 24.5,
  pb_ratio: 4.2,
  dividend_yield: 1.8,
  sector: 'Financials',
  sub_sector: 'Banking',
};

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-1 text-xs border-b border-bloomberg-border/30">
      <span className="text-bloomberg-text-muted">{label}</span>
      <span className="font-mono tabular-nums text-bloomberg-text-primary">{value}</span>
    </div>
  );
}

export default function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const { data: stock, isLoading } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => fetchStockDetail(ticker!),
    placeholderData: mockDetail,
    enabled: !!ticker,
  });

  if (isLoading || !stock) return <LoadingSpinner label={`Loading ${ticker}...`} />;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="text-bloomberg-accent text-xs hover:underline">
          &larr; Back
        </button>
        <h2 className="text-sm font-mono font-bold text-bloomberg-accent">{stock.ticker}</h2>
        <span className="text-xs text-bloomberg-text-secondary">{stock.name}</span>
        <span className="text-xxs text-bloomberg-text-muted bg-bloomberg-bg-tertiary px-2 py-0.5 rounded">
          {stock.sector}
        </span>
      </div>

      <div className="mb-2">
        <PriceDisplay price={stock.last_price} change={stock.change} changePercent={stock.change_pct} size="lg" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <DashboardCard title="Price Summary" dense>
          <StatRow label="Open" value={stock.open.toLocaleString()} />
          <StatRow label="High" value={stock.high.toLocaleString()} />
          <StatRow label="Low" value={stock.low.toLocaleString()} />
          <StatRow label="Volume" value={(stock.volume / 1_000_000).toFixed(1) + 'M'} />
        </DashboardCard>

        <DashboardCard title="Valuation" dense>
          <StatRow label="P/E Ratio" value={stock.pe_ratio.toFixed(1)} />
          <StatRow label="P/B Ratio" value={stock.pb_ratio.toFixed(2)} />
          <StatRow label="Div. Yield" value={stock.dividend_yield.toFixed(1) + '%'} />
          <StatRow label="Market Cap" value={(stock.market_cap / 1e12).toFixed(0) + 'T'} />
        </DashboardCard>

        <DashboardCard title="Chart" dense>
          <div className="h-32 flex items-center justify-center text-bloomberg-text-muted text-xs font-mono">
            Price chart placeholder
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}
