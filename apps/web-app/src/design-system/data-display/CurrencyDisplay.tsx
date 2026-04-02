import { cn } from '@/lib/utils';
import { formatIDR, formatIDRCompact } from '@/lib/format';

interface CurrencyDisplayProps {
  value: number;
  compact?: boolean;
  className?: string;
  colorize?: boolean;
}

function CurrencyDisplay({ value, compact = false, className, colorize = false }: CurrencyDisplayProps) {
  const formatted = compact ? formatIDRCompact(value) : formatIDR(value);

  return (
    <span
      className={cn(
        'tabular-nums',
        colorize && {
          'text-[var(--positive)]': value > 0,
          'text-[var(--negative)]': value < 0,
          'text-[var(--text-primary)]': value === 0,
        },
        className,
      )}
    >
      {colorize && value > 0 && '+'}
      {formatted}
    </span>
  );
}

export { CurrencyDisplay };
