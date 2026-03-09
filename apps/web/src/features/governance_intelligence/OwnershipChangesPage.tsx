import { DashboardCard } from '../../shared_ui_components/DashboardCard';
import { theme } from '../../design_system/bloomberg_dark_theme_tokens';

interface OwnershipChange {
  symbol: string;
  filer: string;
  filerType: string;
  changePct: number;
  eventDate: string;
}

export function OwnershipChangesPage() {
  const changes: OwnershipChange[] = [
    { symbol: 'BBCA', filer: 'Djarum Group', filerType: 'Major Shareholder', changePct: 0.5, eventDate: '2025-03-12' },
    { symbol: 'ASII', filer: 'Jardine Matheson', filerType: 'Major Shareholder', changePct: -1.2, eventDate: '2025-03-10' },
  ];

  return (
    <div className="p-4 space-y-4" style={{ backgroundColor: theme.bg.primary }}>
      <h1 className="text-xl font-bold" style={{ color: theme.text.primary }}>Ownership Changes</h1>
      <DashboardCard title="Recent Filings">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ color: theme.text.secondary }}>
              <th className="text-left py-1">Symbol</th>
              <th className="text-left py-1">Filer</th>
              <th className="text-left py-1">Type</th>
              <th className="text-right py-1">Change %</th>
              <th className="text-right py-1">Date</th>
            </tr>
          </thead>
          <tbody>
            {changes.map((c, i) => (
              <tr key={i} className="border-t" style={{ borderColor: theme.bg.tertiary }}>
                <td className="py-1 font-mono" style={{ color: theme.accent.primary }}>{c.symbol}</td>
                <td className="py-1" style={{ color: theme.text.primary }}>{c.filer}</td>
                <td className="py-1" style={{ color: theme.text.secondary }}>{c.filerType}</td>
                <td className="text-right py-1 font-mono" style={{
                  color: c.changePct > 0 ? theme.semantic.positive : theme.semantic.negative
                }}>
                  {c.changePct > 0 ? '+' : ''}{c.changePct.toFixed(1)}%
                </td>
                <td className="text-right py-1 font-mono" style={{ color: theme.text.secondary }}>{c.eventDate}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DashboardCard>
    </div>
  );
}
