'use client';

import type { ReactNode } from 'react';

/**
 * No-op provider. Smooth (Lenis) scrolling was removed per design feedback —
 * the public site now uses native browser scrolling to match MSCI.com and
 * other large company sites. Kept as a passthrough so existing imports
 * elsewhere don't break, but you should prefer to remove the import.
 */
export function SmoothScrollProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
