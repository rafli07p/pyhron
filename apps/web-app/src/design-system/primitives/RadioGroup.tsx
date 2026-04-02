'use client';

import { forwardRef, createContext, useContext, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface RadioGroupContextValue {
  value?: string;
  onValueChange?: (value: string) => void;
  name?: string;
}

const RadioGroupContext = createContext<RadioGroupContextValue>({});

export interface RadioGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
  onValueChange?: (value: string) => void;
  name?: string;
}

const RadioGroup = forwardRef<HTMLDivElement, RadioGroupProps>(
  ({ className, value, onValueChange, name, ...props }, ref) => (
    <RadioGroupContext.Provider value={{ value, onValueChange, name }}>
      <div ref={ref} role="radiogroup" className={cn('flex flex-col gap-2', className)} {...props} />
    </RadioGroupContext.Provider>
  ),
);
RadioGroup.displayName = 'RadioGroup';

export interface RadioGroupItemProps extends React.HTMLAttributes<HTMLButtonElement> {
  value: string;
  label?: string;
  disabled?: boolean;
}

const RadioGroupItem = forwardRef<HTMLButtonElement, RadioGroupItemProps>(
  ({ className, value, label, disabled, id, ...props }, ref) => {
    const ctx = useContext(RadioGroupContext);
    const checked = ctx.value === value;
    const itemId = id || `radio-${value}`;
    const handleClick = useCallback(() => {
      if (!disabled) ctx.onValueChange?.(value);
    }, [ctx, value, disabled]);

    return (
      <div className="flex items-center gap-2">
        <button
          ref={ref}
          id={itemId}
          type="button"
          role="radio"
          aria-checked={checked}
          disabled={disabled}
          onClick={handleClick}
          className={cn(
            'h-4 w-4 shrink-0 rounded-full border border-[var(--border-default)] bg-[var(--surface-2)] transition-colors',
            'hover:border-[var(--border-hover)]',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-0)]',
            'disabled:cursor-not-allowed disabled:opacity-50',
            checked && 'border-[var(--accent-500)]',
            className,
          )}
          {...props}
        >
          {checked && (
            <span className="flex items-center justify-center">
              <span className="h-2 w-2 rounded-full bg-[var(--accent-500)]" />
            </span>
          )}
        </button>
        {label && (
          <label
            htmlFor={itemId}
            className="text-sm text-[var(--text-primary)] cursor-pointer select-none"
          >
            {label}
          </label>
        )}
        {ctx.name && <input type="hidden" name={ctx.name} value={checked ? value : ''} />}
      </div>
    );
  },
);
RadioGroupItem.displayName = 'RadioGroupItem';

export { RadioGroup, RadioGroupItem };
