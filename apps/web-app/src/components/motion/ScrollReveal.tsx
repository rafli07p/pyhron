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
  className,
}: ScrollRevealProps) {
  return (
    <div className={className}>
      {children}
    </div>
  );
}
