'use client';

import { useConnectionStore } from '@/stores/connection';
import { Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';

export function DegradedBanner() {
  const { api, ws } = useConnectionStore();

  if (api === 'online' && ws !== 'disconnected') return null;

  const isOffline = api === 'offline';
  const isWsDown = ws === 'disconnected' || ws === 'reconnecting';

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-1.5 text-xs font-medium',
        isOffline
          ? 'bg-[var(--negative-muted)] text-[var(--negative)]'
          : 'bg-[var(--warning-muted)] text-[var(--warning)]',
      )}
      role="alert"
    >
      {isOffline ? <WifiOff className="h-3.5 w-3.5" /> : <Wifi className="h-3.5 w-3.5" />}
      {isOffline
        ? 'Connection lost. Displaying cached data. Attempting to reconnect...'
        : ws === 'reconnecting'
          ? 'Real-time updates reconnecting...'
          : 'Real-time updates paused. Data may be delayed.'}
    </div>
  );
}
