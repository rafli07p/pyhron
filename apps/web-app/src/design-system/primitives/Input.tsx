import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, label, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-[var(--text-secondary)]">
            {label}
          </label>
        )}
        <input
          type={type}
          id={inputId}
          className={cn(
            'flex h-9 w-full rounded-md border bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text-primary)] transition-colors',
            'placeholder:text-[var(--text-tertiary)]',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error
              ? 'border-[var(--negative)] focus-visible:ring-[var(--negative)]'
              : 'border-[var(--border-default)] hover:border-[var(--border-hover)]',
            className,
          )}
          ref={ref}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={error ? `${inputId}-error` : undefined}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} className="text-xs text-[var(--negative)]" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = 'Input';

export { Input };
