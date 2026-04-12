'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

const BLUE = '#2563eb';
const GRAY = '#94a3b8';

function IconHome({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <path d="M3 10.5L12 3l9 7.5V21H15v-5a1 1 0 00-1-1h-4a1 1 0 00-1 1v5H3V10.5z" />
    </svg>
  );
}

function IconCompanies({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <rect x="2" y="7" width="8" height="14" rx="1" />
      <rect x="14" y="3" width="8" height="18" rx="1" />
      <line x1="5" y1="10" x2="7" y2="10" /><line x1="5" y1="13" x2="7" y2="13" /><line x1="5" y1="16" x2="7" y2="16" />
      <line x1="17" y1="6" x2="19" y2="6" /><line x1="17" y1="9" x2="19" y2="9" /><line x1="17" y1="12" x2="19" y2="12" /><line x1="17" y1="15" x2="19" y2="15" />
    </svg>
  );
}

function IconPortfolios({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function IconIndexes({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill={active ? BLUE + '15' : 'none'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <rect x="2" y="2" width="20" height="20" rx="3" />
      <polyline points="7 14 10 10 13 13 17 8" />
      <line x1="17" y1="8" x2="17" y2="11" /><line x1="17" y1="8" x2="14" y2="8" />
    </svg>
  );
}

function IconResearch({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="9" rx="1" />
      <rect x="3" y="15" width="7" height="6" rx="1" /><rect x="14" y="15" width="7" height="6" rx="1" />
      <line x1="5" y1="6" x2="8" y2="6" /><line x1="5" y1="8" x2="7" y2="8" />
      <line x1="16" y1="6" x2="19" y2="6" /><line x1="16" y1="8" x2="18" y2="8" />
    </svg>
  );
}

function IconReports({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" />
      <polyline points="14 2 14 8 20 8" />
      <polyline points="8 14 10 16 14 12" />
    </svg>
  );
}

function IconApps({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function IconSettings({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke={active ? BLUE : GRAY}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  );
}

const NAV_ITEMS = [
  { label: 'Home', path: '/dashboard', Icon: IconHome },
  { label: 'Companies', path: '/markets', Icon: IconCompanies },
  { label: 'Portfolios', path: '/portfolio', Icon: IconPortfolios },
  { label: 'Indexes', path: '/studio', Icon: IconIndexes },
  { label: 'Research', path: '/research', Icon: IconResearch },
  { label: 'Reports', path: '/strategies', Icon: IconReports },
  { label: 'Apps', path: '/execution', Icon: IconApps },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { mobileOpen, setMobileOpen } = useSidebarStore();

  const renderLink = (item: { label: string; path: string; Icon: React.FC<{ active: boolean }> }) => {
    const isActive = pathname === item.path || pathname.startsWith(item.path + '/');
    return (
      <Link
        key={item.path}
        href={item.path}
        onClick={() => setMobileOpen(false)}
        className={cn(
          'flex flex-col items-center gap-[5px] py-[10px] transition-colors',
          isActive ? 'text-[#2563eb]' : 'text-[#94a3b8] hover:text-[#64748b]',
        )}
      >
        <item.Icon active={isActive} />
        <span className={cn('text-[10px] leading-none', isActive ? 'font-bold' : 'font-medium')}>
          {item.label}
        </span>
      </Link>
    );
  };

  const sidebarContent = (
    <div className="flex h-full flex-col items-center">
      <nav className="flex flex-1 flex-col items-center gap-0 overflow-y-auto px-1 pt-3">
        {NAV_ITEMS.map((item) => renderLink(item))}
      </nav>

      {/* Settings + shield at bottom */}
      <div className="shrink-0 border-t border-[#e5e7eb] px-1 pb-3 pt-2">
        {renderLink({ label: 'Settings', path: '/settings', Icon: IconSettings })}
        {/* Shield icon at very bottom */}
        <div className="mt-2 flex justify-center">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#2563eb] text-white">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 11 14 15 10" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-[68px] shrink-0 border-r border-[#e5e7eb] bg-white lg:block">
        {sidebarContent}
      </aside>

      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setMobileOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 w-[68px] border-r border-[#e5e7eb] bg-white lg:hidden">
            <div className="flex h-10 items-center justify-center">
              <button onClick={() => setMobileOpen(false)} className="text-[#94a3b8] hover:text-[#475569]" aria-label="Close">
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
