'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Command } from 'cmdk';
import {
  LayoutDashboard, BarChart3, FlaskConical, Briefcase,
  TrendingUp, Settings, Search, ArrowRight,
} from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette';

const PAGES = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, group: 'Pages' },
  { name: 'Markets', href: '/markets', icon: BarChart3, group: 'Pages' },
  { name: 'Stock Screener', href: '/markets/screener', icon: Search, group: 'Pages' },
  { name: 'Research', href: '/research/dashboard', icon: FlaskConical, group: 'Pages' },
  { name: 'Signals', href: '/research/signals', icon: FlaskConical, group: 'Pages' },
  { name: 'Strategies', href: '/strategies', icon: Briefcase, group: 'Pages' },
  { name: 'Portfolio', href: '/portfolio', icon: TrendingUp, group: 'Pages' },
  { name: 'Positions', href: '/portfolio/positions', icon: TrendingUp, group: 'Pages' },
  { name: 'Orders', href: '/portfolio/orders', icon: TrendingUp, group: 'Pages' },
  { name: 'Risk Dashboard', href: '/portfolio/risk', icon: TrendingUp, group: 'Pages' },
  { name: 'Settings', href: '/settings', icon: Settings, group: 'Pages' },
];

export function CommandPalette() {
  const router = useRouter();
  const { open, setOpen } = useCommandPaletteStore();
  const [search, setSearch] = useState('');

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, setOpen]);

  const navigate = (href: string) => {
    setOpen(false);
    setSearch('');
    router.push(href);
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Command palette"
      className="fixed inset-0 z-50"
    >
      <div className="fixed inset-0 bg-black/50" onClick={() => setOpen(false)} />
      <div className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2">
        <div className="overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] shadow-2xl">
          <div className="flex items-center border-b border-[var(--border-default)] px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 text-[var(--text-tertiary)]" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Search pages, instruments, actions..."
              className="flex h-11 w-full bg-transparent py-3 text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-tertiary)]"
            />
          </div>
          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-[var(--text-tertiary)]">
              No results found.
            </Command.Empty>
            <Command.Group heading="Pages" className="text-xs font-semibold text-[var(--text-tertiary)]">
              {PAGES.map((page) => (
                <Command.Item
                  key={page.href}
                  value={page.name}
                  onSelect={() => navigate(page.href)}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-[var(--text-secondary)] aria-selected:bg-[var(--surface-3)] aria-selected:text-[var(--text-primary)]"
                >
                  <page.icon className="h-4 w-4" />
                  <span>{page.name}</span>
                  <ArrowRight className="ml-auto h-3 w-3 opacity-0 aria-selected:opacity-100" />
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </div>
      </div>
    </Command.Dialog>
  );
}
