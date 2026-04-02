'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search, Bell, Globe, Menu } from 'lucide-react';
import { useSession, signOut } from 'next-auth/react';
import { Logo } from '@/components/common/Logo';
import { Button } from '@/design-system/primitives/Button';
import { useCommandPaletteStore } from '@/stores/command-palette';
import { useSidebarStore } from '@/stores/sidebar';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/studio', label: 'Studio' },
  { href: '/markets', label: 'Markets' },
  { href: '/research', label: 'Research' },
  { href: '/portfolio', label: 'Portfolio' },
];

export function TopNav() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const openPalette = useCommandPaletteStore((s) => s.setOpen);
  const toggleMobile = useSidebarStore((s) => s.setMobileOpen);

  return (
    <header className="sticky top-0 z-40 flex h-12 items-center border-b border-[var(--border-default)] bg-[var(--surface-0)]/80 px-4 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <button
          className="rounded-md p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] lg:hidden"
          onClick={() => toggleMobile(true)}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Link href="/dashboard" className="flex items-center">
          <Logo size="sm" />
        </Link>
      </div>

      <nav className="ml-8 hidden items-center gap-1 md:flex" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              pathname.startsWith(item.href)
                ? 'bg-[var(--accent-50)] text-[var(--accent-500)]'
                : 'text-[var(--text-secondary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]',
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="hidden gap-2 text-xs text-[var(--text-tertiary)] sm:flex"
          onClick={() => openPalette(true)}
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search...</span>
          <kbd className="rounded bg-[var(--surface-3)] px-1.5 py-0.5 text-[10px] font-mono">
            ⌘K
          </kbd>
        </Button>

        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </Button>

        <Button variant="ghost" size="icon" aria-label="Language">
          <Globe className="h-4 w-4" />
        </Button>

        {session?.user && (
          <button
            onClick={() => signOut({ callbackUrl: '/login' })}
            className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--accent-500)] text-xs font-medium text-white"
            aria-label="User menu"
          >
            {session.user.name?.charAt(0).toUpperCase() || 'U'}
          </button>
        )}
      </div>
    </header>
  );
}
