import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Logo({ className, size = 'md' }: LogoProps) {
  const sizeClasses = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
  };

  return (
    <span
      className={cn(
        'font-bold tracking-tight text-[var(--text-primary)]',
        sizeClasses[size],
        className,
      )}
    >
      PYHRON
    </span>
  );
}
