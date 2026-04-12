'use client';

import { Bell, HelpCircle, Search, ChevronDown } from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette';

export function TerminalTopBar() {
  const openPalette = useCommandPaletteStore((s) => s.setOpen);
  const activeSection = 'Portfolios';

  return (
    <header className="sticky top-0 z-40 flex h-[48px] shrink-0 items-center bg-[#1b2a3d]">
      {/* Left: Brand */}
      <div className="flex h-full w-[76px] shrink-0 items-center justify-center border-r border-white/[0.08]">
        <span className="text-[13px] font-bold text-white">
          MSCI ONE <span className="text-white/50">◐</span>
        </span>
      </div>

      {/* Center: Section selector + Search */}
      <div className="flex flex-1 items-center gap-3 px-4">
        {/* Section dropdown */}
        <button className="flex items-center gap-1.5 rounded bg-white/[0.08] px-3 py-1.5 text-[12px] font-medium text-white/80 transition-colors hover:bg-white/[0.12]">
          {activeSection}
          <ChevronDown className="h-3 w-3 text-white/40" />
        </button>

        {/* Search */}
        <button
          onClick={() => openPalette(true)}
          className="flex flex-1 max-w-[400px] items-center gap-2 rounded bg-white/[0.06] px-3 py-1.5 text-[12px] text-white/30 transition-colors hover:bg-white/[0.10]"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search</span>
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1 px-3">
        <button className="rounded-full bg-[#22c55e]/20 px-2.5 py-1 text-[10px] font-semibold text-[#4ade80]">
          AskMSCI
        </button>
        <button aria-label="Notifications" className="rounded p-2 text-white/40 hover:bg-white/[0.06] hover:text-white/70">
          <Bell className="h-[18px] w-[18px]" />
        </button>
        <button aria-label="Help" className="rounded p-2 text-white/40 hover:bg-white/[0.06] hover:text-white/70">
          <HelpCircle className="h-[18px] w-[18px]" />
        </button>
        <div className="ml-1 flex h-8 w-8 items-center justify-center rounded-full bg-[#2563eb] text-[11px] font-bold text-white">
          RP
        </div>
      </div>
    </header>
  );
}
