'use client';

import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export function RefreshButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      onClick={() => startTransition(() => router.refresh())}
      disabled={pending}
      className={cn(
        'inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
        'border-[var(--color-border)] bg-[var(--color-bg-card)] text-[var(--color-text-primary)]',
        'hover:bg-[var(--color-border-subtle,#F0F4F8)] disabled:opacity-60',
      )}
      aria-label="Refresh orderbook"
    >
      <RefreshCw className={cn('h-3.5 w-3.5', pending && 'animate-spin')} />
      {pending ? 'Refreshing…' : 'Refresh'}
    </button>
  );
}
