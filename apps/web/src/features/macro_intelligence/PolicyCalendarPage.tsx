import DashboardCard from '@/shared_ui_components/DashboardCard';

interface PolicyEvent {
  date: string;
  event: string;
  institution: string;
  impact: 'high' | 'medium' | 'low';
  previous?: string;
  forecast?: string;
}

const events: PolicyEvent[] = [
  { date: '2026-03-19', event: 'BI Board of Governors Meeting', institution: 'Bank Indonesia', impact: 'high', previous: '6.00%', forecast: '6.00%' },
  { date: '2026-03-25', event: 'Trade Balance (Feb)', institution: 'BPS', impact: 'medium', previous: '$3.56B' },
  { date: '2026-04-01', event: 'CPI Inflation (Mar)', institution: 'BPS', impact: 'high', previous: '2.84%', forecast: '2.75%' },
  { date: '2026-04-02', event: 'Manufacturing PMI (Mar)', institution: 'S&P Global', impact: 'medium', previous: '52.1' },
  { date: '2026-04-15', event: 'FX Reserves (Mar)', institution: 'Bank Indonesia', impact: 'low', previous: '$145.2B' },
  { date: '2026-04-22', event: 'BI Board of Governors Meeting', institution: 'Bank Indonesia', impact: 'high', previous: '6.00%' },
  { date: '2026-05-05', event: 'GDP Growth Q1 2026', institution: 'BPS', impact: 'high', previous: '5.05%' },
];

const impactBadge: Record<string, string> = {
  high: 'bg-bloomberg-red/20 text-bloomberg-red',
  medium: 'bg-bloomberg-yellow/20 text-bloomberg-yellow',
  low: 'bg-bloomberg-bg-tertiary text-bloomberg-text-muted',
};

export default function PolicyCalendarPage() {
  const upcoming = events.filter((e) => e.date >= '2026-03-09');
  const past = events.filter((e) => e.date < '2026-03-09');

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-mono font-semibold uppercase tracking-wider">
        Policy & Economic Calendar
      </h2>

      <DashboardCard title="Upcoming Events">
        <div className="space-y-1">
          {upcoming.map((ev, i) => (
            <div key={i} className="flex items-center gap-3 py-2 px-2 border-b border-bloomberg-border/30 hover:bg-bloomberg-bg-tertiary transition-colors text-xs">
              <span className="font-mono text-bloomberg-accent w-20 shrink-0">{ev.date}</span>
              <span className={`px-1.5 py-0.5 rounded text-xxs font-semibold uppercase ${impactBadge[ev.impact]}`}>
                {ev.impact}
              </span>
              <span className="text-bloomberg-text-primary flex-1">{ev.event}</span>
              <span className="text-bloomberg-text-muted w-28 text-right">{ev.institution}</span>
              <span className="font-mono text-bloomberg-text-secondary w-16 text-right">
                {ev.forecast ?? '--'}
              </span>
              <span className="font-mono text-bloomberg-text-muted w-16 text-right">
                {ev.previous ?? '--'}
              </span>
            </div>
          ))}
        </div>
      </DashboardCard>

      {past.length > 0 && (
        <DashboardCard title="Recent Events" subtitle="Past">
          <div className="space-y-1">
            {past.map((ev, i) => (
              <div key={i} className="flex items-center gap-3 py-2 px-2 text-xs opacity-60">
                <span className="font-mono w-20 shrink-0">{ev.date}</span>
                <span className="flex-1">{ev.event}</span>
                <span className="font-mono text-bloomberg-text-muted w-16 text-right">{ev.previous ?? '--'}</span>
              </div>
            ))}
          </div>
        </DashboardCard>
      )}
    </div>
  );
}
