'use client';

import { Bell, Globe, Search } from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette';

export function TerminalTopBar() {
  const openPalette = useCommandPaletteStore((s) => s.setOpen);

  return (
    <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center justify-between border-b border-[var(--border-default)] bg-[var(--surface-1)] px-4">
      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold tracking-[0.2em] text-[var(--text-primary)]">
          PYHRON
        </span>
        <span className="font-mono text-xs font-bold text-[var(--accent-400)]">ONE</span>
      </div>

      {/* Center: Search */}
      <button
        onClick={() => openPalette(true)}
        className="hidden items-center gap-2 rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-1 text-xs text-[var(--text-tertiary)] transition-colors hover:border-[var(--text-tertiary)] sm:flex"
        style={{ width: 264 }}
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="rounded bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-[10px]">
          ⌘K
        </kbd>
      </button>

      {/* Right: Icons + Avatar */}
      <div className="flex items-center gap-2">
        <button
          aria-label="Notifications"
          className="rounded-md p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
        >
          <Bell className="h-4 w-4" />
        </button>
        <button
          aria-label="Language"
          className="rounded-md p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
        >
          <Globe className="h-4 w-4" />
        </button>
        <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--accent-500)]/30 bg-[var(--accent-500)]/10 text-[10px] font-bold text-[var(--accent-400)]">
          RP
        </div>
      </div>
    </header>
  );
}
