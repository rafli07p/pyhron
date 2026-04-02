import { cn } from '@/lib/utils';
import { Button } from '@/design-system/primitives/Button';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {Icon && (
        <div className="mb-4 rounded-full bg-[var(--surface-2)] p-3">
          <Icon className="h-6 w-6 text-[var(--text-tertiary)]" />
        </div>
      )}
      <h3 className="text-sm font-medium text-[var(--text-primary)]">{title}</h3>
      {description && (
        <p className="mt-1 text-sm text-[var(--text-tertiary)]">{description}</p>
      )}
      {action && (
        <Button variant="outline" size="sm" className="mt-4" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

export { EmptyState };
