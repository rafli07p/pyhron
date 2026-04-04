'use client';

import { useEffect } from 'react';
import { gsap } from '@/lib/gsap-setup';

export function useHeroAnimation(containerRef: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.fromTo(
      el.querySelectorAll('.hero-line'),
      { y: 60, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, stagger: 0.15 },
      0.3,
    );

    tl.from(
      el.querySelector('.hero-subtext'),
      { y: 30, opacity: 0, duration: 0.8 },
      '-=0.4',
    );

    tl.from(
      el.querySelector('.hero-cta'),
      { y: 20, opacity: 0, duration: 0.6 },
      '-=0.3',
    );

    tl.from(
      el.querySelector('.hero-scroll-indicator'),
      { opacity: 0, duration: 0.5 },
      '-=0.2',
    );

    return () => {
      tl.kill();
    };
  }, [containerRef]);
}
