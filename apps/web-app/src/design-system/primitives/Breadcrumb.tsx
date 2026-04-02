'use client';

import { forwardRef } from 'react';
import { ChevronRight } from 'lucide-react';
import { getBreadcrumbs, type RouteConfig } from '@/constants/routes';
import { cn } from '@/lib/utils';

export interface BreadcrumbProps extends React.HTMLAttributes<HTMLElement> {
  path: string;
  onNavigate?: (path: string) => void;
}

const Breadcrumb = forwardRef<HTMLElement, BreadcrumbProps>(
  ({ className, path, onNavigate, ...props }, ref) => {
    const crumbs = getBreadcrumbs(path);

    if (crumbs.length === 0) return null;

    return (
      <nav ref={ref} aria-label="Breadcrumb" className={cn('flex items-center', className)} {...props}>
        <ol className="flex items-center gap-1 text-sm">
          {crumbs.map((crumb: RouteConfig, index: number) => {
            const isLast = index === crumbs.length - 1;
            return (
              <li key={crumb.path} className="flex items-center gap-1">
                {index > 0 && (
                  <ChevronRight className="h-3.5 w-3.5 text-[var(--text-tertiary)]" aria-hidden />
                )}
                {isLast ? (
                  <span className="font-medium text-[var(--text-primary)]" aria-current="page">
                    {crumb.label}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => onNavigate?.(crumb.path)}
                    className="text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
                  >
                    {crumb.label}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    );
  },
);
Breadcrumb.displayName = 'Breadcrumb';

export { Breadcrumb };
