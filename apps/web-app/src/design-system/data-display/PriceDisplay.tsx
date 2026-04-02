'use client';

import { cn } from '@/lib/utils';
import { formatIDR } from '@/lib/format';

interface PriceDisplayProps {
  price: number;
  previousPrice?: number;
  className?: string;
  showCurrency?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function PriceDisplay({
  price,
  previousPrice,
  className,
  showCurrency = true,
  size = 'md',
}: PriceDisplayProps) {
  const prev = previousPrice ?? price;
  const direction = price > prev ? 'up' : price < prev ? 'down' : null;

  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl font-semibold',
  };

  return (
    <span
      // Key changes on price to retrigger CSS animation
      key={price}
      className={cn(
        'tabular-nums transition-colors',
        sizeClasses[size],
        direction === 'up' && 'animate-tick-up',
        direction === 'down' && 'animate-tick-down',
        className,
      )}
    >
      {showCurrency ? formatIDR(price) : price.toLocaleString('id-ID')}
    </span>
  );
}

export { PriceDisplay };
