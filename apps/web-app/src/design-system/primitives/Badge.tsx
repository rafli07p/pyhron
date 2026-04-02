import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-[var(--surface-3)] text-[var(--text-secondary)]',
        accent: 'bg-[var(--accent-100)] text-[var(--accent-500)]',
        positive: 'bg-[var(--positive-muted)] text-[var(--positive)]',
        negative: 'bg-[var(--negative-muted)] text-[var(--negative)]',
        warning: 'bg-[var(--warning-muted)] text-[var(--warning)]',
        info: 'bg-[var(--info-muted)] text-[var(--info)]',
        outline: 'border border-[var(--border-default)] text-[var(--text-secondary)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
