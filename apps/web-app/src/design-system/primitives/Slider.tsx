'use client';

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  min?: number;
  max?: number;
  step?: number;
  value?: number;
  onChange?: (value: number) => void;
}

const Slider = forwardRef<HTMLInputElement, SliderProps>(
  ({ className, min = 0, max = 100, step = 1, value, onChange, disabled, ...props }, ref) => (
    <input
      ref={ref}
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange?.(Number(e.target.value))}
      className={cn(
        'h-1.5 w-full cursor-pointer appearance-none rounded-full bg-[var(--surface-3)] outline-none transition-opacity',
        'focus-visible:ring-2 focus-visible:ring-[var(--accent-500)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-0)]',
        'disabled:cursor-not-allowed disabled:opacity-50',
        '[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--accent-500)] [&::-webkit-slider-thumb]:transition-colors [&::-webkit-slider-thumb]:hover:bg-[var(--accent-600)]',
        '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-[var(--accent-500)] [&::-moz-range-thumb]:transition-colors [&::-moz-range-thumb]:hover:bg-[var(--accent-600)]',
        className,
      )}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      {...props}
    />
  ),
);
Slider.displayName = 'Slider';

export { Slider };
