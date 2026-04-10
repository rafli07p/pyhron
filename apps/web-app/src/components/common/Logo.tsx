import { cn } from '@/lib/utils';
import Image from 'next/image';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Logo({ className, size: _size = 'md' }: LogoProps) {
  return (
      <Image
          src="/logos/logo.svg"
          alt="Pyhron"
          width={120}
          height={32}
          priority
          className={cn('h-8 w-auto dark:hidden', className)}
      />
  );
}
