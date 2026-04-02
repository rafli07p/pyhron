import { ArrowUp, ArrowDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PercentChangeProps {
  value: number;
  className?: string;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

function PercentChange({ value, className, showIcon = true, size = 'md' }: PercentChangeProps) {
  const isPositive = value > 0;
  const isNegative = value < 0;

  const Icon = isPositive ? ArrowUp : isNegative ? ArrowDown : Minus;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 tabular-nums font-medium',
        {
          'text-[var(--positive)]': isPositive,
          'text-[var(--negative)]': isNegative,
          'text-[var(--text-tertiary)]': !isPositive && !isNegative,
        },
        size === 'sm' ? 'text-xs' : 'text-sm',
        className,
      )}
      aria-label={`${isPositive ? 'Up' : isNegative ? 'Down' : 'Unchanged'} ${Math.abs(value).toFixed(2)}%`}
    >
      {showIcon && <Icon className={size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'} />}
      {isPositive && '+'}
      {value.toFixed(2)}%
    </span>
  );
}

export { PercentChange };
