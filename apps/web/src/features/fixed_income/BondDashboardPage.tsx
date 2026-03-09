import DashboardCard from '@/shared_ui_components/DashboardCard';
import DataTable, { type Column } from '@/shared_ui_components/DataTable';

interface BondRow {
  isin: string;
  series: string;
  type: 'Government' | 'Corporate';
  coupon: number;
  maturity: string;
  yield_pct: number;
  price: number;
  duration: number;
  rating: string;
  [key: string]: unknown;
}

const mockBonds: BondRow[] = [
  { isin: 'IDG000013806', series: 'FR0098', type: 'Government', coupon: 7.125, maturity: '2030-06-15', yield_pct: 6.72, price: 101.85, duration: 4.2, rating: 'BBB' },
  { isin: 'IDG000014200', series: 'FR0100', type: 'Government', coupon: 6.875, maturity: '2028-03-15', yield_pct: 6.48, price: 100.95, duration: 2.1, rating: 'BBB' },
  { isin: 'IDG000015100', series: 'FR0102', type: 'Government', coupon: 7.375, maturity: '2035-09-15', yield_pct: 7.08, price: 102.45, duration: 7.8, rating: 'BBB' },
  { isin: 'IDCORP001001', series: 'BBCA01', type: 'Corporate', coupon: 8.250, maturity: '2027-12-01', yield_pct: 7.85, price: 100.72, duration: 1.8, rating: 'AAA(idn)' },
  { isin: 'IDCORP001002', series: 'TLKM01', type: 'Corporate', coupon: 7.950, maturity: '2029-06-15', yield_pct: 7.62, price: 101.15, duration: 3.2, rating: 'AAA(idn)' },
  { isin: 'IDCORP001003', series: 'BMRI02', type: 'Corporate', coupon: 8.500, maturity: '2028-09-01', yield_pct: 8.05, price: 100.95, duration: 2.5, rating: 'AA+(idn)' },
];

const columns: Column<BondRow>[] = [
  { key: 'series', label: 'Series', align: 'left', sortable: true, render: (r) => <span className="text-bloomberg-accent font-bold">{r.series}</span> },
  { key: 'type', label: 'Type', align: 'left', sortable: true, render: (r) => <span className={r.type === 'Government' ? 'text-bloomberg-blue' : 'text-bloomberg-yellow'}>{r.type}</span> },
  { key: 'coupon', label: 'Coupon', align: 'right', sortable: true, render: (r) => `${r.coupon.toFixed(3)}%` },
  { key: 'maturity', label: 'Maturity', align: 'right', sortable: true },
  { key: 'yield_pct', label: 'Yield', align: 'right', sortable: true, render: (r) => `${r.yield_pct.toFixed(2)}%` },
  { key: 'price', label: 'Price', align: 'right', sortable: true, render: (r) => r.price.toFixed(2) },
  { key: 'duration', label: 'Dur', align: 'right', sortable: true, render: (r) => r.duration.toFixed(1) },
  { key: 'rating', label: 'Rating', align: 'center', sortable: true },
];

export default function BondDashboardPage() {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Fixed Income Dashboard
      </h2>

      <div className="grid grid-cols-4 gap-2">
        <DashboardCard title="10Y SBN Yield" dense>
          <div className="text-lg font-mono font-bold text-bloomberg-text-primary tabular-nums">6.95%</div>
          <div className="text-xxs text-bloomberg-red">+3 bps</div>
        </DashboardCard>
        <DashboardCard title="Foreign Holdings" dense>
          <div className="text-lg font-mono font-bold text-bloomberg-text-primary tabular-nums">14.2%</div>
          <div className="text-xxs text-bloomberg-text-muted">of outstanding SBN</div>
        </DashboardCard>
        <DashboardCard title="SBN Outstanding" dense>
          <div className="text-lg font-mono font-bold text-bloomberg-text-primary tabular-nums">Rp5,420T</div>
          <div className="text-xxs text-bloomberg-text-muted">Total government bonds</div>
        </DashboardCard>
        <DashboardCard title="Bid-Cover Ratio" dense>
          <div className="text-lg font-mono font-bold text-bloomberg-green tabular-nums">2.45x</div>
          <div className="text-xxs text-bloomberg-text-muted">Last auction</div>
        </DashboardCard>
      </div>

      <DashboardCard title="Bond Universe" subtitle="Government + Corporate">
        <DataTable columns={columns} data={mockBonds} rowKey={(r) => r.isin} />
      </DashboardCard>
    </div>
  );
}
