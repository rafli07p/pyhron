'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface DataFreshnessProps {
  lastUpdate: number | null;
  staleThreshold?: number;
  className?: string;
}

function DataFreshness({ lastUpdate, staleThreshold = 30_000, className }: DataFreshnessProps) {
  const [age, setAge] = useState<string>('--');
  const [isStale, setIsStale] = useState(false);

  useEffect(() => {
    if (!lastUpdate) return;

    const update = () => {
      const diff = Date.now() - lastUpdate;
      setIsStale(diff > staleThreshold);

      if (diff < 1000) setAge('<1s');
      else if (diff < 60_000) setAge(`${Math.floor(diff / 1000)}s`);
      else if (diff < 3_600_000) setAge(`${Math.floor(diff / 60_000)}m`);
      else setAge(`${Math.floor(diff / 3_600_000)}h`);
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [lastUpdate, staleThreshold]);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-xs tabular-nums',
        isStale ? 'text-[var(--warning)]' : 'text-[var(--text-tertiary)]',
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', isStale ? 'bg-[var(--warning)]' : 'bg-[var(--positive)]')} />
      {isStale ? `Stale (${age})` : `${age} ago`}
    </span>
  );
}

export { DataFreshness };
