import DashboardCard from '@/shared_ui_components/DashboardCard';

interface HotspotRegion {
  province: string;
  hotspots: number;
  change_vs_avg: number;
  fire_risk: 'high' | 'medium' | 'low';
  rainfall_mm: number;
  rainfall_vs_avg: number;
}

const mockData: HotspotRegion[] = [
  { province: 'Riau', hotspots: 245, change_vs_avg: 32, fire_risk: 'high', rainfall_mm: 42, rainfall_vs_avg: -58 },
  { province: 'South Sumatra', hotspots: 189, change_vs_avg: 18, fire_risk: 'high', rainfall_mm: 55, rainfall_vs_avg: -45 },
  { province: 'Central Kalimantan', hotspots: 312, change_vs_avg: 45, fire_risk: 'high', rainfall_mm: 38, rainfall_vs_avg: -62 },
  { province: 'West Kalimantan', hotspots: 134, change_vs_avg: 12, fire_risk: 'medium', rainfall_mm: 88, rainfall_vs_avg: -28 },
  { province: 'South Kalimantan', hotspots: 78, change_vs_avg: -5, fire_risk: 'medium', rainfall_mm: 105, rainfall_vs_avg: -15 },
  { province: 'East Kalimantan', hotspots: 56, change_vs_avg: -12, fire_risk: 'low', rainfall_mm: 142, rainfall_vs_avg: 5 },
];

const riskBadge: Record<string, string> = {
  high: 'bg-bloomberg-red/20 text-bloomberg-red',
  medium: 'bg-bloomberg-yellow/20 text-bloomberg-yellow',
  low: 'bg-bloomberg-green/20 text-bloomberg-green',
};

export default function ClimateOverlayPage() {
  const totalHotspots = mockData.reduce((s, r) => s + r.hotspots, 0);

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Climate & Fire Hotspot Overlay
      </h2>

      <div className="grid grid-cols-3 gap-2">
        <DashboardCard title="Total Hotspots" dense>
          <div className="text-2xl font-mono font-bold text-bloomberg-red tabular-nums">{totalHotspots}</div>
          <div className="text-xxs text-bloomberg-text-muted">Active fire hotspots (MODIS/VIIRS)</div>
        </DashboardCard>
        <DashboardCard title="CPO Supply Impact" dense>
          <div className="text-2xl font-mono font-bold text-bloomberg-yellow tabular-nums">Medium</div>
          <div className="text-xxs text-bloomberg-text-muted">Based on plantation proximity</div>
        </DashboardCard>
        <DashboardCard title="El Nino Status" dense>
          <div className="text-2xl font-mono font-bold text-bloomberg-accent tabular-nums">Neutral</div>
          <div className="text-xxs text-bloomberg-text-muted">ENSO index: -0.2</div>
        </DashboardCard>
      </div>

      <DashboardCard title="Provincial Hotspot & Rainfall Data">
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-bloomberg-text-muted text-xxs uppercase tracking-wider">
                <th className="text-left px-2 py-1.5 border-b border-bloomberg-border">Province</th>
                <th className="text-right px-2 py-1.5 border-b border-bloomberg-border">Hotspots</th>
                <th className="text-right px-2 py-1.5 border-b border-bloomberg-border">vs Avg</th>
                <th className="text-center px-2 py-1.5 border-b border-bloomberg-border">Risk</th>
                <th className="text-right px-2 py-1.5 border-b border-bloomberg-border">Rain (mm)</th>
                <th className="text-right px-2 py-1.5 border-b border-bloomberg-border">Rain vs Avg</th>
              </tr>
            </thead>
            <tbody>
              {mockData.map((r) => (
                <tr key={r.province} className="border-b border-bloomberg-border/30 hover:bg-bloomberg-bg-tertiary">
                  <td className="text-left px-2 py-1">{r.province}</td>
                  <td className="text-right px-2 py-1 tabular-nums">{r.hotspots}</td>
                  <td className={`text-right px-2 py-1 tabular-nums ${r.change_vs_avg > 0 ? 'text-bloomberg-red' : 'text-bloomberg-green'}`}>
                    {r.change_vs_avg > 0 ? '+' : ''}{r.change_vs_avg}%
                  </td>
                  <td className="text-center px-2 py-1">
                    <span className={`px-1.5 py-0.5 rounded text-xxs font-semibold uppercase ${riskBadge[r.fire_risk]}`}>{r.fire_risk}</span>
                  </td>
                  <td className="text-right px-2 py-1 tabular-nums">{r.rainfall_mm}</td>
                  <td className={`text-right px-2 py-1 tabular-nums ${r.rainfall_vs_avg < 0 ? 'text-bloomberg-red' : 'text-bloomberg-green'}`}>
                    {r.rainfall_vs_avg > 0 ? '+' : ''}{r.rainfall_vs_avg}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DashboardCard>
    </div>
  );
}
