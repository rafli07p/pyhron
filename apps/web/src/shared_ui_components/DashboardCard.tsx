import { type ReactNode } from 'react';

interface DashboardCardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  dense?: boolean;
}

export { DashboardCard };
export default function DashboardCard({
  title,
  subtitle,
  action,
  children,
  className = '',
  dense = false,
}: DashboardCardProps) {
  return (
    <div
      className={`bg-bloomberg-bg-secondary border border-bloomberg-border rounded-md overflow-hidden ${className}`}
    >
      <div className="px-3 py-2 border-b border-bloomberg-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-mono font-semibold text-bloomberg-text-primary uppercase tracking-wider">
            {title}
          </h3>
          {subtitle && (
            <span className="text-xxs text-bloomberg-text-muted font-mono">{subtitle}</span>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
      <div className={dense ? 'p-2' : 'p-3'}>{children}</div>
    </div>
  );
}
