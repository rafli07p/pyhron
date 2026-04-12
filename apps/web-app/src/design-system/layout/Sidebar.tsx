'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

/**
 * MSCI One sidebar — exact match to Image 4.
 * Light blue icons on dark navy bg. Active = filled blue with bold label.
 * No logo text inside sidebar. Clean vertical list.
 */

type NavItem = { label: string; path: string; d: string };

// SVG path data for each icon — clean outline style matching MSCI One
const NAV: NavItem[] = [
  {
    label: 'Home',
    path: '/dashboard',
    // House icon
    d: 'M3 10.5L12 3l9 7.5V20a1.5 1.5 0 01-1.5 1.5H4.5A1.5 1.5 0 013 20V10.5z M9 21V14h6v7',
  },
  {
    label: 'Companies',
    path: '/markets',
    // Building grid icon
    d: 'M3 7h7v14H3V7zm0 0V4.5A1.5 1.5 0 014.5 3h5A1.5 1.5 0 0111 4.5V7m3 0h7v14h-7V7zm0 0V4.5A1.5 1.5 0 0115.5 3h5A1.5 1.5 0 0122 4.5V7 M6 11h1m-1 3h1m-1 3h1m10-6h1m-1 3h1m-1 3h1',
  },
  {
    label: 'Portfolios',
    path: '/portfolio',
    // Clipboard check icon
    d: 'M9 2h6v3a1 1 0 01-1 1h-4a1 1 0 01-1-1V2zm-3 4h12a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2z M9 14l2 2 4-4',
  },
  {
    label: 'Indexes',
    path: '/studio',
    // Pulse/chart line icon
    d: 'M22 12h-4l-3 9L9 3l-3 9H2',
  },
  {
    label: 'Research',
    path: '/research',
    // Magnifier with plus icon
    d: 'M11 3a8 8 0 100 16 8 8 0 000-16zm10 18l-4.35-4.35 M8 11h6m-3-3v6',
  },
  {
    label: 'Reports',
    path: '/strategies',
    // Document icon
    d: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm0 0v6h6 M8 13h8m-8 4h8',
  },
  {
    label: 'Apps',
    path: '/execution',
    // Grid 2x2 icon
    d: 'M3 3h7v7H3V3zm11 0h7v7h-7V3zM3 14h7v7H3v-7zm11 0h7v7h-7v-7z',
  },
];

const SETTINGS: NavItem = {
  label: 'Settings',
  path: '/settings',
  // Gear icon
  d: 'M12 15a3 3 0 100-6 3 3 0 000 6z M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z',
};

function NavIcon({ d, active }: { d: string; active: boolean }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={active ? 2.2 : 1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={d} />
    </svg>
  );
}

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
          'flex flex-col items-center gap-1 py-2.5 transition-colors',
          isActive ? 'text-[#4a9eff]' : 'text-[#6b87a8] hover:text-[#a0c4e8]',
        )}
      >
        <NavIcon d={item.d} active={isActive} />
        <span className={cn('text-[10px] leading-tight', isActive ? 'font-bold' : 'font-medium')}>
          {item.label}
        </span>
      </Link>
    );
  };

  const sidebarContent = (
    <div className="flex h-full flex-col items-center">
      {/* Nav items */}
      <nav className="flex flex-1 flex-col items-center gap-1 overflow-y-auto px-1 pt-3">
        {NAV.map(renderLink)}
      </nav>

      {/* Settings at bottom */}
      <div className="shrink-0 border-t border-white/[0.08] px-1 pb-3 pt-2">
        {renderLink(SETTINGS)}
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-[68px] shrink-0 bg-[#1b2a3d] lg:block">
        {sidebarContent}
      </aside>

      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 w-[68px] bg-[#1b2a3d] lg:hidden">
            <div className="flex h-12 items-center justify-center">
              <button onClick={() => setMobileOpen(false)} className="text-white/40 hover:text-white/80" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  );
}
