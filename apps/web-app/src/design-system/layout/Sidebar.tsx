'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

/**
 * MSCI One-style sidebar — icon above label, centered, narrow column.
 * Each item is an icon (SVG) stacked above a short text label.
 */

const NAV_ITEMS = [
  {
    label: 'Home',
    path: '/dashboard',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
        <polyline points="9 21 9 14 15 14 15 21" />
      </svg>
    ),
  },
  {
    label: 'Markets',
    path: '/markets',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    label: 'Portfolios',
    path: '/portfolio',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" />
        <rect x="8" y="2" width="8" height="4" rx="1" />
        <path d="M9 14l2 2 4-4" />
      </svg>
    ),
  },
  {
    label: 'Indexes',
    path: '/studio',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    label: 'Research',
    path: '/research',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
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
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    label: 'Apps',
    path: '/execution',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
      </svg>
    ),
  },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { mobileOpen, setMobileOpen } = useSidebarStore();

  const renderLink = (item: typeof NAV_ITEMS[number], index: number) => {
    const isActive = pathname === item.path || pathname.startsWith(item.path + '/');
    return (
      <Link
        key={item.path}
        href={item.path}
        onClick={() => setMobileOpen(false)}
        className={cn(
          'group flex flex-col items-center gap-1 py-3 transition-colors',
          isActive
            ? 'text-[#2563eb]'
            : 'text-white/35 hover:text-white/70',
        )}
      >
        <div className={cn(
          'flex h-9 w-9 items-center justify-center rounded-lg transition-colors',
          isActive ? 'bg-[#2563eb]/10' : 'group-hover:bg-white/[0.04]',
        )}>
          {item.icon}
        </div>
        <span className="text-[10px] font-medium">{item.label}</span>
      </Link>
    );
  };

  const content = (
    <div className="flex h-full flex-col items-center">
      {/* Logo */}
      <div className="flex h-12 w-full items-center justify-center border-b border-white/[0.08]">
        <Link href="/dashboard" className="text-[11px] font-bold tracking-[0.1em] text-white/60">
          P
        </Link>
      </div>

      {/* Navigation items */}
      <nav className="flex flex-1 flex-col items-center gap-0 overflow-y-auto px-1.5 py-2">
        {NAV_ITEMS.slice(0, -1).map(renderLink)}
      </nav>

      {/* Settings at bottom */}
      <div className="border-t border-white/[0.06] px-1.5 py-2">
        {renderLink(NAV_ITEMS[NAV_ITEMS.length - 1]!, NAV_ITEMS.length - 1)}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar — MSCI One style: narrow icon+label column */}
      <aside className="hidden w-[72px] shrink-0 border-r border-white/[0.06] bg-[#0f1923] lg:block">
        {content}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 w-[72px] border-r border-white/[0.06] bg-[#0f1923] lg:hidden">
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
