'use client';

import { useRef, useEffect, type ElementType } from 'react';
import { gsap, ScrollTrigger } from '@/lib/gsap-setup';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface TextRevealProps {
  children: string;
  as?: ElementType;
  splitBy?: 'lines' | 'words';
  stagger?: number;
  className?: string;
}

export function TextReveal({
  children,
  as: Tag = 'p',
  splitBy = 'words',
  stagger = 0.08,
  className,
}: TextRevealProps) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();

  const pieces = splitBy === 'lines' ? children.split('\n') : children.split(' ');

  useEffect(() => {
    const el = ref.current;
    if (reduced || !el) return;

    const inners = el.querySelectorAll('.text-reveal-inner');
    const tween = gsap.from(inners, {
      y: '100%',
      duration: 0.6,
      stagger,
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
  }, [stagger, reduced]);

  const Component = Tag as 'div';
  return (
    <Component ref={ref as React.Ref<HTMLDivElement>} className={className} aria-label={children}>
      {pieces.map((piece, i) => (
        <span
          key={i}
          className="inline-block overflow-hidden"
          aria-hidden="true"
        >
          <span className="text-reveal-inner inline-block">
            {piece}
            {splitBy === 'words' && i < pieces.length - 1 ? '\u00A0' : ''}
          </span>
        </span>
      ))}
    </Component>
  );
}
