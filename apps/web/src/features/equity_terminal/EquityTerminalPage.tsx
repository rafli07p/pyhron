import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import DashboardCard from '@/shared_ui_components/DashboardCard';
import DataTable, { type Column } from '@/shared_ui_components/DataTable';
import PriceDisplay from '@/shared_ui_components/PriceDisplay';
import LoadingSpinner from '@/shared_ui_components/LoadingSpinner';
import { fetchWatchlist, type WatchlistItem } from '@/api_client/equity_api_client';

const columns: Column<WatchlistItem>[] = [
  {
    key: 'ticker',
    label: 'Ticker',
    align: 'left',
    sortable: true,
    render: (r) => <span className="text-bloomberg-accent font-bold">{r.ticker}</span>,
  },
  { key: 'name', label: 'Name', align: 'left', sortable: true },
  {
    key: 'last_price',
    label: 'Last',
    align: 'right',
    sortable: true,
    render: (r) => (
      <PriceDisplay price={r.last_price} change={r.change} changePercent={r.change_pct} size="sm" />
    ),
  },
  {
    key: 'volume',
    label: 'Vol (M)',
    align: 'right',
    sortable: true,
    render: (r) => <span className="tabular-nums">{(r.volume / 1_000_000).toFixed(1)}</span>,
  },
  {
    key: 'market_cap',
    label: 'MCap (T)',
    align: 'right',
    sortable: true,
    render: (r) => (
      <span className="tabular-nums">{(r.market_cap / 1_000_000_000_000).toFixed(1)}</span>
    ),
  },
];

const mockData: WatchlistItem[] = [
  { ticker: 'BBCA', name: 'Bank Central Asia', last_price: 9825, change: 75, change_pct: 0.77, volume: 42_300_000, market_cap: 1_210_000_000_000_000 },
  { ticker: 'BBRI', name: 'Bank Rakyat Indonesia', last_price: 5475, change: -25, change_pct: -0.45, volume: 89_100_000, market_cap: 823_000_000_000_000 },
  { ticker: 'TLKM', name: 'Telkom Indonesia', last_price: 3960, change: 10, change_pct: 0.25, volume: 56_200_000, market_cap: 392_000_000_000_000 },
  { ticker: 'ASII', name: 'Astra International', last_price: 5150, change: -50, change_pct: -0.96, volume: 31_400_000, market_cap: 208_000_000_000_000 },
  { ticker: 'BMRI', name: 'Bank Mandiri', last_price: 6300, change: 50, change_pct: 0.8, volume: 44_700_000, market_cap: 588_000_000_000_000 },
];

export default function EquityTerminalPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: fetchWatchlist,
    placeholderData: mockData,
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-mono font-semibold text-bloomberg-text-primary uppercase tracking-wider">
          IDX Equity Terminal
        </h2>
        <span className="text-xxs text-bloomberg-text-muted font-mono">
          IHSG Last: 7,234.56 | USD/IDR: 15,845
        </span>
      </div>

      <DashboardCard title="Watchlist" subtitle="LQ45">
        {isLoading ? (
          <LoadingSpinner size="sm" label="Loading watchlist..." />
        ) : (
          <DataTable
            columns={columns}
            data={data ?? []}
            rowKey={(r) => r.ticker}
            onRowClick={(r) => navigate(`/stock/${r.ticker}`)}
          />
        )}
      </DashboardCard>
    </div>
  );
}
