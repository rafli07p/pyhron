'use client';

import Image from 'next/image';
import { Search, ChevronDown } from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette';

const activeSection = 'Portfolios';

export function TerminalTopBar() {
  const openPalette = useCommandPaletteStore((s) => s.setOpen);

  return (
    <header className="sticky top-0 z-40 flex h-[40px] shrink-0 items-center justify-between bg-[#1c2b3a] px-0">
      {/* Left: Logo */}
      <div className="flex h-full items-center gap-1.5 pl-4 pr-6">
        <span className="text-[14px] font-bold tracking-wide text-white">MSCI ONE</span>
        <span className="text-[14px] text-white/40">◐</span>
      </div>

      {/* Center: Section selector + Search */}
      <div className="flex flex-1 items-center gap-2">
        <button className="flex items-center gap-1 rounded-[4px] border border-white/[0.15] bg-white/[0.06] px-3 py-[5px] text-[12px] font-medium text-white transition-colors hover:bg-white/[0.10]">
          {activeSection}
          <ChevronDown className="h-3 w-3 text-white/40" />
        </button>

        <button
          onClick={() => openPalette(true)}
          className="flex w-[280px] items-center gap-2 rounded-[4px] border border-white/[0.15] bg-white/[0.06] px-3 py-[5px] text-[12px] text-white/35 transition-colors hover:bg-white/[0.10]"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search</span>
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-0.5 pr-3">
        {/* AskMSCI badge */}
        <button className="mr-1 flex items-center gap-1 rounded-full bg-[#166534] px-2.5 py-[3px] text-[10px] font-bold text-[#4ade80]">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10" /></svg>
          AskMSCI
          <span className="rounded bg-[#22c55e]/30 px-1 text-[8px] font-bold text-[#86efac]">BETA</span>
        </button>

        <button aria-label="Notifications" className="rounded p-1.5 text-white/50 hover:text-white/80">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" />
          </svg>
        </button>

        <button aria-label="Help" className="rounded p-1.5 text-white/50 hover:text-white/80">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </button>

        <button aria-label="Settings" className="rounded p-1.5 text-white/50 hover:text-white/80">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
          </svg>
        </button>

        {/* User avatar */}
        <div className="ml-1 flex h-[28px] w-[28px] items-center justify-center rounded-full bg-[#3b5998] text-[10px] font-bold text-white">
          RP
        </div>
      </div>
    </header>
  );
}
