import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn('mb-6 flex items-start justify-between', className)}>
      <div>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
