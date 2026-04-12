'use client';

import type { ReactNode } from 'react';

type Preset = 'fadeUp' | 'fadeLeft' | 'fadeRight' | 'scaleIn';

interface ScrollRevealProps {
  children: ReactNode;
  preset?: Preset;
  delay?: number;
  duration?: number;
  stagger?: number;
  className?: string;
}

export function ScrollReveal({ children, className }: ScrollRevealProps) {
  return (
    <div className={className}>
      {children}
    </div>
  );
}
