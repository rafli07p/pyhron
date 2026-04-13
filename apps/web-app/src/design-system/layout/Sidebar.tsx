'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

const C = '#2e7de6';
const G = '#8fa8c8';

function IHome({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 11.4L12 4l8 7.4V21H15v-5.5a1 1 0 00-1-1h-4a1 1 0 00-1 1V21H4V11.4z" /></svg>);
}
function ICompanies({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="8" width="8" height="13" rx="1" /><rect x="14" y="3" width="8" height="18" rx="1" /><line x1="5" y1="11" x2="7" y2="11" /><line x1="5" y1="14" x2="7" y2="14" /><line x1="5" y1="17" x2="7" y2="17" /><line x1="17" y1="6" x2="19" y2="6" /><line x1="17" y1="9" x2="19" y2="9" /><line x1="17" y1="12" x2="19" y2="12" /><line x1="17" y1="15" x2="19" y2="15" /></svg>);
}
function IPortfolios({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="17" rx="2.5" /><path d="M9 12.5l2 2 4-4" /></svg>);
}
function IIndexes({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill={a ? c + '18' : 'none'} stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2.5" y="2.5" width="19" height="19" rx="3" /><polyline points="7 15 10.5 10 13.5 13 17 8" strokeWidth="1.8" /><polyline points="15 8 17 8 17 10" strokeWidth="1.8" /></svg>);
}
function IResearch({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="9" height="8" rx="1.5" /><rect x="13" y="3" width="9" height="8" rx="1.5" /><rect x="2" y="13" width="9" height="8" rx="1.5" /><rect x="13" y="13" width="9" height="8" rx="1.5" /><line x1="5" y1="6" x2="8" y2="6" /><line x1="5" y1="8" x2="7" y2="8" /><line x1="16" y1="6" x2="19" y2="6" /><line x1="16" y1="8" x2="18" y2="8" /><line x1="5" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="19" y2="16" /></svg>);
}
function IReports({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" /><polyline points="14 2 14 8 20 8" /><line x1="8" y1="13" x2="16" y2="13" /><line x1="8" y1="17" x2="13" y2="17" /></svg>);
}
function IApps({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7.5" height="7.5" rx="1.5" /><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" /><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" /><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" /></svg>);
}
function ISettings({ a }: { a: boolean }) {
  const c = a ? C : G;
  return (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>);
}

type Item = { label: string; path: string; Icon: React.FC<{ a: boolean }> };

const NAV: Item[] = [
  { label: 'Home', path: '/dashboard', Icon: IHome },
  { label: 'Companies', path: '/markets', Icon: ICompanies },
  { label: 'Portfolios', path: '/portfolio', Icon: IPortfolios },
  { label: 'Indexes', path: '/studio', Icon: IIndexes },
  { label: 'Research', path: '/research', Icon: IResearch },
  { label: 'Reports', path: '/strategies', Icon: IReports },
  { label: 'Apps', path: '/execution', Icon: IApps },
];

export function Sidebar() {
  const pathname = usePathname();
  const { mobileOpen, setMobileOpen } = useSidebarStore();

  const renderLink = (item: Item) => {
    const active = pathname === item.path || pathname.startsWith(item.path + '/');
    return (
      <Link key={item.path} href={item.path} onClick={() => setMobileOpen(false)}
        className={cn('flex flex-col items-center gap-[3px] py-[12px] transition-colors', active ? 'text-[#2e7de6]' : 'text-[#8fa8c8] hover:text-[#5b7fa3]')}>
        <item.Icon a={active} />
        <span className={cn('text-[9px] leading-none', active ? 'font-bold' : 'font-medium')}>{item.label}</span>
      </Link>
    );
  };

  const content = (
    <div className="flex h-full flex-col items-center">
      <nav className="flex flex-1 flex-col items-center justify-start gap-0 pt-1">{NAV.map(renderLink)}</nav>
      <div className="shrink-0 border-t border-[#e2e8f0] pt-1 pb-2">
        {renderLink({ label: 'Settings', path: '/settings', Icon: ISettings })}
        <div className="mt-1 flex justify-center">
          <div className="flex h-[28px] w-[28px] items-center justify-center rounded-md bg-[#2e7de6]">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><polyline points="9 12 11 14 15 10" /></svg>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-[62px] shrink-0 border-r border-[#e2e8f0] bg-white lg:block">{content}</aside>
      {mobileOpen && (<>
        <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setMobileOpen(false)} />
        <aside className="fixed inset-y-0 left-0 z-50 w-[62px] border-r border-[#e2e8f0] bg-white lg:hidden">
          <div className="flex h-10 items-center justify-center"><button onClick={() => setMobileOpen(false)} className="text-[#8fa8c8]" aria-label="Close"><X className="h-4 w-4" /></button></div>
          {content}
        </aside>
      </>)}
    </>
  );
}
