'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronLeft, X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { ROUTES } from '@/constants/routes';
import { Badge } from '@/design-system/primitives/Badge';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, mobileOpen, toggle, setMobileOpen } = useSidebarStore();

  const sidebarRoutes = Object.values(ROUTES).filter((r) => r.showInSidebar);
  const mainRoutes = sidebarRoutes.filter((r) => r.sidebarGroup === 'main');
  const advancedRoutes = sidebarRoutes.filter((r) => r.sidebarGroup === 'advanced');
  const systemRoutes = sidebarRoutes.filter((r) => r.sidebarGroup === 'system');

  const renderLink = (route: (typeof ROUTES)[string]) => {
    const Icon = route.icon;
    const isActive = pathname === route.path || pathname.startsWith(route.path + '/');
    return (
      <Link
        key={route.path}
        href={route.path}
        onClick={() => setMobileOpen(false)}
        className={cn(
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-[var(--accent-50)] text-[var(--accent-500)]'
            : 'text-[var(--text-secondary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]',
          collapsed && 'justify-center px-2',
        )}
        title={collapsed ? route.labelEn : undefined}
      >
        {Icon && <Icon className="h-4 w-4 shrink-0" />}
        {!collapsed && (
          <>
            <span className="truncate">{route.labelEn}</span>
            {route.badge && (
              <Badge
                variant={route.badge === 'beta' ? 'warning' : route.badge === 'pro' ? 'accent' : 'info'}
                className="ml-auto text-[10px]"
              >
                {route.badge}
              </Badge>
            )}
          </>
        )}
      </Link>
    );
  };

  const renderGroup = (label: string, routes: typeof mainRoutes) => {
    if (routes.length === 0) return null;
    return (
      <div className="space-y-1">
        {!collapsed && (
          <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
            {label}
          </p>
        )}
        {routes.map(renderLink)}
      </div>
    );
  };

  const content = (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-2 py-4">
        {renderGroup('Main', mainRoutes)}
        {renderGroup('Advanced', advancedRoutes)}
        {renderGroup('System', systemRoutes)}
      </div>

      <div className="border-t border-[var(--border-default)] p-2">
        <button
          onClick={toggle}
          className="hidden w-full items-center justify-center rounded-md p-2 text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)] lg:flex"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')} />
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden border-r border-[var(--border-default)] bg-[var(--surface-1)] transition-[width] duration-200 lg:block',
          collapsed ? 'w-14' : 'w-60',
        )}
      >
        {content}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 w-60 border-r border-[var(--border-default)] bg-[var(--surface-1)] lg:hidden">
            <div className="flex h-12 items-center justify-between border-b border-[var(--border-default)] px-4">
              <span className="text-sm font-semibold text-[var(--text-primary)]">Navigation</span>
              <button
                onClick={() => setMobileOpen(false)}
                className="rounded-md p-1 text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
                aria-label="Close menu"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {content}
          </aside>
        </>
      )}
    </>
  );
}
