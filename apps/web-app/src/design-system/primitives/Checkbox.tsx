'use client';

import { forwardRef } from 'react';
import * as CheckboxPrimitive from '@radix-ui/react-checkbox';
import { Check, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CheckboxProps
  extends React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root> {
  label?: string;
}

const Checkbox = forwardRef<React.ComponentRef<typeof CheckboxPrimitive.Root>, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const checkboxId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="flex items-center gap-2">
        <CheckboxPrimitive.Root
          ref={ref}
          id={checkboxId}
          className={cn(
            'peer h-4 w-4 shrink-0 rounded border border-[var(--border-default)] bg-[var(--surface-2)] transition-colors',
            'hover:border-[var(--border-hover)]',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-0)]',
            'data-[state=checked]:border-[var(--accent-500)] data-[state=checked]:bg-[var(--accent-500)]',
            'data-[state=indeterminate]:border-[var(--accent-500)] data-[state=indeterminate]:bg-[var(--accent-500)]',
            'disabled:cursor-not-allowed disabled:opacity-50',
            className,
          )}
          {...props}
        >
          <CheckboxPrimitive.Indicator className="flex items-center justify-center text-white">
            {props.checked === 'indeterminate' ? (
              <Minus className="h-3 w-3" />
            ) : (
              <Check className="h-3 w-3" />
            )}
          </CheckboxPrimitive.Indicator>
        </CheckboxPrimitive.Root>
        {label && (
          <label
            htmlFor={checkboxId}
            className="text-sm text-[var(--text-primary)] cursor-pointer select-none peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
          >
            {label}
          </label>
        )}
      </div>
    );
  },
);
Checkbox.displayName = 'Checkbox';

export { Checkbox };
