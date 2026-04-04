'use client';

import { useEffect, type ReactNode } from 'react';
import { gsap, ScrollTrigger } from '@/lib/gsap-setup';
import { useReducedMotion } from '@/hooks/useReducedMotion';

export function SmoothScrollProvider({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) return;

    let lenis: import('lenis').default | null = null;
    let rafId: ReturnType<typeof gsap.ticker.add> | null = null;

    (async () => {
      const Lenis = (await import('lenis')).default;
      lenis = new Lenis({
        duration: 1.2,
        easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        orientation: 'vertical',
        smoothWheel: true,
      });

      lenis.on('scroll', ScrollTrigger.update);

      const raf = (time: number) => {
        lenis?.raf(time * 1000);
      };
      gsap.ticker.add(raf);
      gsap.ticker.lagSmoothing(0);
      rafId = raf as unknown as ReturnType<typeof gsap.ticker.add>;
    })();

    return () => {
      if (lenis) lenis.destroy();
      if (rafId) gsap.ticker.remove(rafId as unknown as gsap.TickerCallback);
    };
  }, [reduced]);

  return <>{children}</>;
}
