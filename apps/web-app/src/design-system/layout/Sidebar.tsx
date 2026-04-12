'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  {
    label: 'Home',
    path: '/dashboard',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 10.5L12 3l9 7.5V21a1 1 0 01-1 1H4a1 1 0 01-1-1V10.5z" />
        <polyline points="9 21 9 14 15 14 15 21" />
      </svg>
    ),
  },
  {
    label: 'Companies',
    path: '/markets',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="7" width="7" height="14" rx="1" />
        <rect x="14" y="3" width="7" height="18" rx="1" />
        <line x1="6" y1="11" x2="7" y2="11" />
        <line x1="6" y1="14" x2="7" y2="14" />
        <line x1="17" y1="7" x2="18" y2="7" />
        <line x1="17" y1="10" x2="18" y2="10" />
        <line x1="17" y1="13" x2="18" y2="13" />
      </svg>
    ),
  },
  {
    label: 'Portfolios',
    path: '/portfolio',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={active ? 0 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        {active ? (
          <>
            <rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor" opacity="0.15" />
            <path d="M8 12l3 3 5-6" stroke="currentColor" strokeWidth="2" fill="none" />
          </>
        ) : (
          <>
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <path d="M8 12l3 3 5-6" />
          </>
        )}
      </svg>
    ),
  },
  {
    label: 'Indexes',
    path: '/studio',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    label: 'Research',
    path: '/research',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="8" y1="11" x2="14" y2="11" />
        <line x1="11" y1="8" x2="11" y2="14" />
      </svg>
    ),
  },
  {
    label: 'Reports',
    path: '/strategies',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
  {
    label: 'Apps',
    path: '/execution',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
] as const;

const SETTINGS_ITEM = {
  label: 'Settings',
  path: '/settings',
  icon: (active: boolean) => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.5} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
};

type NavItem = { label: string; path: string; icon: (active: boolean) => React.ReactNode };

export function Sidebar() {
  const pathname = usePathname();
  const { mobileOpen, setMobileOpen } = useSidebarStore();

  const renderLink = (item: NavItem) => {
    const isActive = pathname === item.path || pathname.startsWith(item.path + '/');
    return (
      <Link
        key={item.path}
        href={item.path}
        onClick={() => setMobileOpen(false)}
        className={cn(
          'group flex flex-col items-center gap-[6px] py-[10px] transition-colors',
          isActive ? 'text-[#3b82f6]' : 'text-[#7b8fa3] hover:text-[#b0c4de]',
        )}
      >
        {item.icon(isActive)}
        <span className={cn(
          'text-[10px] leading-none',
          isActive ? 'font-semibold' : 'font-medium',
        )}>
          {item.label}
        </span>
      </Link>
    );
  };

  const content = (
    <div className="flex h-full flex-col items-center">
      {/* Logo area — aligned with topbar height */}
      <div className="flex h-[48px] w-full shrink-0 items-center justify-center">
        <span className="text-[11px] font-bold tracking-wider text-white/50">MSCI <span className="text-white/30">◐</span></span>
      </div>

      {/* Main nav items */}
      <nav className="flex flex-1 flex-col items-center gap-[2px] overflow-y-auto px-2 pt-1">
        {(NAV_ITEMS as unknown as NavItem[]).map(renderLink)}
      </nav>

      {/* Settings at bottom */}
      <div className="shrink-0 border-t border-white/[0.06] px-2 py-2">
        {renderLink(SETTINGS_ITEM)}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-[76px] shrink-0 border-r border-white/[0.06] bg-[#1b2a3d] lg:block">
        {content}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 w-[76px] border-r border-white/[0.06] bg-[#1b2a3d] lg:hidden">
            <div className="flex h-12 items-center justify-center border-b border-white/[0.06]">
              <button onClick={() => setMobileOpen(false)} className="text-white/40 hover:text-white/80" aria-label="Close menu">
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
