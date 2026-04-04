'use client';

import { useRef, useEffect } from 'react';
import { gsap, ScrollTrigger } from '@/lib/gsap-setup';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface CountUpProps {
  end: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  decimals?: number;
  className?: string;
}

export function CountUp({
  end,
  prefix = '',
  suffix = '',
  duration = 1.5,
  decimals = 0,
  className,
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (reduced) {
      el.textContent = `${prefix}${end.toFixed(decimals)}${suffix}`;
      return;
    }

    const counter = { value: 0 };
    const fmt = new Intl.NumberFormat('id-ID', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });

    const tween = gsap.to(counter, {
      value: end,
      duration,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 90%',
        toggleActions: 'play none none none',
      },
      onUpdate: () => {
        el.textContent = `${prefix}${fmt.format(counter.value)}${suffix}`;
      },
    });

    return () => {
      tween.kill();
      ScrollTrigger.getAll().forEach((st) => {
        if (st.trigger === el) st.kill();
      });
    };
  }, [end, prefix, suffix, duration, decimals, reduced]);

  return (
    <span
      ref={ref}
      className={`tabular-nums ${className ?? ''}`}
      aria-label={`${prefix}${end}${suffix}`}
    >
      {prefix}0{suffix}
    </span>
  );
}
