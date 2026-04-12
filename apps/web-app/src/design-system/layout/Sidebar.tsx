'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { label: 'Home', path: '/dashboard' },
  { label: 'Markets', path: '/markets' },
  { label: 'Portfolios', path: '/portfolio' },
  { label: 'Research', path: '/research' },
  { label: 'Strategies', path: '/strategies' },
  { label: 'Execution', path: '/execution' },
  { label: 'Reports', path: '/studio' },
  { label: 'Settings', path: '/settings' },
] as const;

const LABS_ITEMS = [
  { label: 'Labs', path: '/ml' },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { mobileOpen, setMobileOpen } = useSidebarStore();

  const renderLink = (item: { label: string; path: string }) => {
    const isActive = pathname === item.path || pathname.startsWith(item.path + '/');
    return (
      <Link
        key={item.path}
        href={item.path}
        onClick={() => setMobileOpen(false)}
        className={cn(
          'flex items-center px-4 py-2.5 text-[13px] font-medium transition-colors',
          isActive
            ? 'border-l-[3px] border-[#2563eb] bg-[#2563eb]/[0.08] pl-[13px] text-[#2563eb]'
            : 'border-l-[3px] border-transparent pl-[13px] text-white/50 hover:bg-white/[0.04] hover:text-white/80',
        )}
      >
        {item.label}
      </Link>
    );
  };

  const content = (
    <div className="flex h-full flex-col">
      {/* Main navigation */}
      <nav className="flex-1 overflow-y-auto py-3">
        <div className="space-y-0.5">
          {NAV_ITEMS.map(renderLink)}
        </div>

        {/* Separator */}
        <div className="my-3 border-t border-white/[0.06]" />

        {/* Labs section */}
        <div className="space-y-0.5">
          {LABS_ITEMS.map(renderLink)}
        </div>
      </nav>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar — fixed width, dark background */}
      <aside className="hidden w-[140px] shrink-0 border-r border-white/[0.06] bg-[#0a0e14] lg:block">
        {content}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 w-[200px] border-r border-white/[0.06] bg-[#0a0e14] lg:hidden">
            <div className="flex h-12 items-center justify-between border-b border-white/[0.06] px-4">
              <span className="text-[13px] font-semibold text-white/80">Navigation</span>
              <button
                onClick={() => setMobileOpen(false)}
                className="rounded-md p-1 text-white/40 hover:text-white/80"
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
