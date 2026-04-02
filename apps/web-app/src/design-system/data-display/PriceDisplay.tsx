'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { formatIDR } from '@/lib/format';

interface PriceDisplayProps {
  price: number;
  previousPrice?: number;
  className?: string;
  showCurrency?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function PriceDisplay({ price, previousPrice, className, showCurrency = true, size = 'md' }: PriceDisplayProps) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);
  const prevRef = useRef(previousPrice ?? price);

  useEffect(() => {
    if (price > prevRef.current) {
      setFlash('up');
    } else if (price < prevRef.current) {
      setFlash('down');
    }
    prevRef.current = price;

    const timer = setTimeout(() => setFlash(null), 600);
    return () => clearTimeout(timer);
  }, [price]);

  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl font-semibold',
  };

  return (
    <span
      className={cn(
        'tabular-nums transition-colors',
        sizeClasses[size],
        flash === 'up' && 'animate-tick-up',
        flash === 'down' && 'animate-tick-down',
        className,
      )}
    >
      {showCurrency ? formatIDR(price) : price.toLocaleString('id-ID')}
    </span>
  );
}

export { PriceDisplay };
