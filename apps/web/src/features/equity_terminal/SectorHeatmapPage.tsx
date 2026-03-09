import DashboardCard from '@/shared_ui_components/DashboardCard';

interface SectorData {
  name: string;
  change_pct: number;
  market_cap_trn: number;
  top_stock: string;
}

const sectors: SectorData[] = [
  { name: 'Financials', change_pct: 0.82, market_cap_trn: 4120, top_stock: 'BBCA' },
  { name: 'Consumer Staples', change_pct: -0.34, market_cap_trn: 890, top_stock: 'UNVR' },
  { name: 'Telecom', change_pct: 0.25, market_cap_trn: 620, top_stock: 'TLKM' },
  { name: 'Energy', change_pct: 1.45, market_cap_trn: 510, top_stock: 'ADRO' },
  { name: 'Materials', change_pct: -1.12, market_cap_trn: 380, top_stock: 'ANTM' },
  { name: 'Industrials', change_pct: -0.55, market_cap_trn: 340, top_stock: 'ASII' },
  { name: 'Property', change_pct: 0.15, market_cap_trn: 210, top_stock: 'BSDE' },
  { name: 'Healthcare', change_pct: 0.92, market_cap_trn: 160, top_stock: 'KLBF' },
  { name: 'Technology', change_pct: 2.10, market_cap_trn: 120, top_stock: 'GOTO' },
  { name: 'Infrastructure', change_pct: -0.08, market_cap_trn: 95, top_stock: 'JSMR' },
];

function heatColor(pct: number): string {
  if (pct > 1.5) return 'bg-green-700';
  if (pct > 0.5) return 'bg-green-800/80';
  if (pct > 0) return 'bg-green-900/60';
  if (pct > -0.5) return 'bg-red-900/60';
  if (pct > -1.5) return 'bg-red-800/80';
  return 'bg-red-700';
}

export default function SectorHeatmapPage() {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Sector Performance Heatmap
      </h2>

      <DashboardCard title="IDX Sectors" subtitle="Today">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
          {sectors.map((s) => (
            <div
              key={s.name}
              className={`${heatColor(s.change_pct)} rounded-md p-3 border border-bloomberg-border/30 hover:border-bloomberg-border transition-colors cursor-pointer`}
            >
              <div className="text-xs font-semibold text-bloomberg-text-primary truncate">
                {s.name}
              </div>
              <div className={`text-lg font-mono font-bold tabular-nums ${s.change_pct >= 0 ? 'text-bloomberg-green' : 'text-bloomberg-red'}`}>
                {s.change_pct > 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xxs text-bloomberg-text-muted">{s.top_stock}</span>
                <span className="text-xxs text-bloomberg-text-muted">{s.market_cap_trn}T</span>
              </div>
            </div>
          ))}
        </div>
      </DashboardCard>

      <DashboardCard title="Market Summary" dense>
        <div className="grid grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <div className="text-bloomberg-text-muted text-xxs">IHSG</div>
            <div className="text-bloomberg-green font-semibold">7,234.56 +0.45%</div>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs">Advancers</div>
            <div className="text-bloomberg-green font-semibold">284</div>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs">Decliners</div>
            <div className="text-bloomberg-red font-semibold">198</div>
          </div>
          <div>
            <div className="text-bloomberg-text-muted text-xxs">Unchanged</div>
            <div className="text-bloomberg-text-secondary font-semibold">143</div>
          </div>
        </div>
      </DashboardCard>
    </div>
  );
}
