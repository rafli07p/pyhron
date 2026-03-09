import DashboardCard from '@/shared_ui_components/DashboardCard';
import DataTable, { type Column } from '@/shared_ui_components/DataTable';

interface ImpactRow {
  ticker: string;
  name: string;
  commodity: string;
  correlation: number;
  beta: number;
  stock_change_1m: number;
  commodity_change_1m: number;
  [key: string]: unknown;
}

const mockData: ImpactRow[] = [
  { ticker: 'ADRO', name: 'Adaro Energy', commodity: 'Coal', correlation: 0.91, beta: 1.35, stock_change_1m: -3.2, commodity_change_1m: -4.8 },
  { ticker: 'PTBA', name: 'Bukit Asam', commodity: 'Coal', correlation: 0.88, beta: 1.22, stock_change_1m: -2.8, commodity_change_1m: -4.8 },
  { ticker: 'AALI', name: 'Astra Agro Lestari', commodity: 'CPO', correlation: 0.82, beta: 0.95, stock_change_1m: 1.5, commodity_change_1m: 2.1 },
  { ticker: 'LSIP', name: 'London Sumatra', commodity: 'CPO', correlation: 0.79, beta: 0.88, stock_change_1m: 1.2, commodity_change_1m: 2.1 },
  { ticker: 'ANTM', name: 'Aneka Tambang', commodity: 'Nickel', correlation: 0.75, beta: 1.10, stock_change_1m: 2.8, commodity_change_1m: 3.5 },
  { ticker: 'INCO', name: 'Vale Indonesia', commodity: 'Nickel', correlation: 0.72, beta: 1.05, stock_change_1m: 2.5, commodity_change_1m: 3.5 },
  { ticker: 'MEDC', name: 'Medco Energi', commodity: 'ICP', correlation: 0.68, beta: 0.82, stock_change_1m: -1.8, commodity_change_1m: -2.5 },
];

const columns: Column<ImpactRow>[] = [
  { key: 'ticker', label: 'Ticker', align: 'left', sortable: true, render: (r) => <span className="text-bloomberg-accent font-bold">{r.ticker}</span> },
  { key: 'name', label: 'Name', align: 'left' },
  { key: 'commodity', label: 'Commodity', align: 'left', sortable: true, render: (r) => <span className="text-bloomberg-yellow">{r.commodity}</span> },
  { key: 'correlation', label: 'Corr', align: 'right', sortable: true, render: (r) => r.correlation.toFixed(2) },
  { key: 'beta', label: 'Beta', align: 'right', sortable: true, render: (r) => r.beta.toFixed(2) },
  { key: 'stock_change_1m', label: 'Stock 1M%', align: 'right', sortable: true, render: (r) => <span className={r.stock_change_1m >= 0 ? 'text-bloomberg-green' : 'text-bloomberg-red'}>{r.stock_change_1m > 0 ? '+' : ''}{r.stock_change_1m.toFixed(1)}%</span> },
  { key: 'commodity_change_1m', label: 'Cmdty 1M%', align: 'right', sortable: true, render: (r) => <span className={r.commodity_change_1m >= 0 ? 'text-bloomberg-green' : 'text-bloomberg-red'}>{r.commodity_change_1m > 0 ? '+' : ''}{r.commodity_change_1m.toFixed(1)}%</span> },
];

export default function StockImpactPage() {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Commodity-to-Stock Impact Analysis
      </h2>

      <DashboardCard title="Correlation Matrix" subtitle="IDX Commodity Plays">
        <DataTable columns={columns} data={mockData} rowKey={(r) => r.ticker} />
      </DashboardCard>

      <DashboardCard title="Impact Summary" dense>
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div>
            <div className="text-bloomberg-text-muted text-xxs mb-1">Strongest Correlation</div>
            <span className="font-mono text-bloomberg-accent">ADRO</span>
            <span className="text-bloomberg-text-muted"> &harr; Coal (0.91)</span>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs mb-1">Highest Beta</div>
            <span className="font-mono text-bloomberg-accent">ADRO</span>
            <span className="text-bloomberg-text-muted"> (1.35x Coal)</span>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs mb-1">Divergence Alert</div>
            <span className="font-mono text-bloomberg-yellow">None detected</span>
          </div>
        </div>
      </DashboardCard>
    </div>
  );
}
