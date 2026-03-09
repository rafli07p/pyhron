import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface GovernanceFlag {
  symbol: string;
  flagType: string;
  severity: string;
  title: string;
  eventDate: string;
}

export function GovernanceDashboardPage() {
  const flags: GovernanceFlag[] = [
    { symbol: 'BUMI', flagType: 'AUDIT_OPINION', severity: 'HIGH', title: 'Qualified audit opinion FY2024', eventDate: '2025-03-15' },
    { symbol: 'LPKR', flagType: 'OWNERSHIP_CHANGE', severity: 'MEDIUM', title: 'Director sold 2.5% stake', eventDate: '2025-03-10' },
    { symbol: 'ELTY', flagType: 'SHARE_PLEDGE', severity: 'CRITICAL', title: 'Commissioner pledged 45% holdings', eventDate: '2025-03-08' },
  ];

  const severityColor = (s: string) => {
    switch (s) {
      case 'CRITICAL': return '#ff1744';
      case 'HIGH': return '#ff6600';
      case 'MEDIUM': return '#ffab00';
      default: return theme.text.secondary;
    }
  };

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>Governance Intelligence</h1>
      <DashboardCard title="Recent Governance Flags">
        <div className="space-y-2">
          {flags.map((f, i) => (
            <div key={i} className="flex items-center justify-between p-2 rounded" style={{ backgroundColor: theme.bg.tertiary }}>
              <div className="flex items-center gap-3">
                <span className="font-mono font-bold" style={{ color: theme.accent.primary }}>{f.symbol}</span>
                <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: severityColor(f.severity), color: '#000' }}>
                  {f.severity}
                </span>
                <span className="text-sm" style={{ color: theme.text.primary }}>{f.title}</span>
              </div>
              <span className="text-xs font-mono" style={{ color: theme.text.secondary }}>{f.eventDate}</span>
            </div>
          ))}
        </div>
      </DashboardCard>
    </div>
  );
}
