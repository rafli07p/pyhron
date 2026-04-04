'use client';

import { useRef, useEffect, type ReactNode } from 'react';
import { gsap, ScrollTrigger } from '@/lib/gsap-setup';
import { useReducedMotion } from '@/hooks/useReducedMotion';

type Preset = 'fadeUp' | 'fadeLeft' | 'fadeRight' | 'scaleIn';

const presetVars: Record<Preset, gsap.TweenVars> = {
  fadeUp: { y: 40, opacity: 0 },
  fadeLeft: { x: -40, opacity: 0 },
  fadeRight: { x: 40, opacity: 0 },
  scaleIn: { scale: 0.92, opacity: 0 },
};

interface ScrollRevealProps {
  children: ReactNode;
  preset?: Preset;
  delay?: number;
  duration?: number;
  stagger?: number;
  className?: string;
}

export function ScrollReveal({
  children,
  preset = 'fadeUp',
  delay = 0,
  duration = 0.8,
  stagger,
  className,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (reduced || !el) return;

    const targets = stagger ? Array.from(el.children) : [el];

    const tween = gsap.from(targets, {
      ...presetVars[preset],
      duration,
      delay,
      stagger: stagger ?? 0,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        toggleActions: 'play none none none',
      },
    });

    return () => {
      tween.kill();
      ScrollTrigger.getAll().forEach((st) => {
        if (st.trigger === el) st.kill();
      });
    };
  }, [preset, delay, duration, stagger, reduced]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
