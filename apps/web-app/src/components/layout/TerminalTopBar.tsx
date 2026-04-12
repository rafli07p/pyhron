'use client';

import { Bell, Globe, Search } from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette';

export function TerminalTopBar() {
  const openPalette = useCommandPaletteStore((s) => s.setOpen);

  return (
    <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center justify-between border-b border-white/[0.08] bg-[#0f1923] px-4">
      {/* Left: Brand */}
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-bold tracking-[0.15em] text-white">
          PYHRON
        </span>
        <span className="text-[13px] font-bold text-white/40">ONE</span>
      </div>

      {/* Center: Search */}
      <button
        onClick={() => openPalette(true)}
        className="hidden items-center gap-2 rounded-md border border-white/[0.12] bg-white/[0.05] px-3 py-1.5 text-[12px] text-white/40 transition-colors hover:border-white/20 sm:flex"
        style={{ width: 280 }}
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-white/30">
          ⌘K
        </kbd>
      </button>

      {/* Right: Icons + Avatar */}
      <div className="flex items-center gap-1.5">
        <button aria-label="Notifications" className="rounded-md p-2 text-white/40 transition-colors hover:bg-white/[0.06] hover:text-white/70">
          <Bell className="h-4 w-4" />
        </button>
        <button aria-label="Language" className="rounded-md p-2 text-white/40 transition-colors hover:bg-white/[0.06] hover:text-white/70">
          <Globe className="h-4 w-4" />
        </button>
        <div className="ml-1 flex h-8 w-8 items-center justify-center rounded-full bg-[#2563eb] text-[11px] font-bold text-white">
          RP
        </div>
      </div>
    </header>
  );
}
