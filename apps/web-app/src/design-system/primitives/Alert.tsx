import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const alertVariants = cva(
  'relative w-full rounded-lg border p-4 text-sm',
  {
    variants: {
      variant: {
        default: 'border-[var(--border-default)] bg-[var(--surface-2)] text-[var(--text-primary)]',
        positive: 'border-[var(--positive)] bg-[var(--positive-muted)] text-[var(--positive)]',
        negative: 'border-[var(--negative)] bg-[var(--negative-muted)] text-[var(--negative)]',
        warning: 'border-[var(--warning)] bg-[var(--warning-muted)] text-[var(--warning)]',
        info: 'border-[var(--info)] bg-[var(--info-muted)] text-[var(--info)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

function Alert({ className, variant, ...props }: AlertProps) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}

function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h5 className={cn('mb-1 font-medium leading-none', className)} {...props} />;
}

function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm opacity-90', className)} {...props} />;
}

export { Alert, AlertTitle, AlertDescription };
