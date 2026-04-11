'use client';

import { useEffect, useMemo, useState } from 'react';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface LiveCounterProps {
  /** Starting value. */
  start: number;
  /** Increment per real-time second. */
  ratePerSecond: number;
  /** Decimals kept in `Intl.NumberFormat`. Defaults to 0. */
  decimals?: number;
  /** Locale passed to `Intl.NumberFormat`. Defaults to id-ID (thousand dots). */
  locale?: string;
  /** String prepended to the formatted number. */
  prefix?: string;
  /** String appended to the formatted number. */
  suffix?: string;
  className?: string;
  ariaLabel?: string;
}

/**
 * Continuously ticking counter intended for hero "data points" style metrics.
 *
 * Unlike `CountUp` — which animates from 0 → `end` once on scroll — this
 * component keeps climbing forever (at `ratePerSecond` units per second) so
 * the metric feels live. Respects `prefers-reduced-motion` by showing the
 * static starting value.
 */
export function LiveCounter({
  start,
  ratePerSecond,
  decimals = 0,
  locale = 'id-ID',
  prefix = '',
  suffix = '',
  className,
  ariaLabel,
}: LiveCounterProps) {
  const reduced = useReducedMotion();
  const format = useMemo(
    () =>
      new Intl.NumberFormat(locale, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }),
    [locale, decimals],
  );
  // We keep the raw numeric value in state; the effect (an external
  // requestAnimationFrame subscription) pushes new values on each frame.
  // When `reduced` is true we skip the tick entirely and render `start`
  // directly during render, so no setState-in-effect is needed.
  const [value, setValue] = useState<number>(start);

  useEffect(() => {
    if (reduced) return;

    let raf = 0;
    const startedAt = performance.now();

    const tick = (now: number) => {
      const elapsed = (now - startedAt) / 1000;
      setValue(start + elapsed * ratePerSecond);
      raf = window.requestAnimationFrame(tick);
    };

    raf = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(raf);
  }, [start, ratePerSecond, reduced]);

  const display = reduced ? format.format(start) : format.format(value);

  return (
    <span
      className={`tabular-nums ${className ?? ''}`}
      aria-label={ariaLabel ?? `${prefix}${format.format(start)}${suffix}`}
    >
      {prefix}
      {display}
      {suffix}
    </span>
  );
}
