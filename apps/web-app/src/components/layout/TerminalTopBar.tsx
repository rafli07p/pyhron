'use client';

import Image from 'next/image';
import { useCommandPaletteStore } from '@/stores/command-palette';

export function TerminalTopBar() {
  const openPalette = useCommandPaletteStore((s) => s.setOpen);

  return (
    <header className="sticky top-0 z-40 flex h-[40px] shrink-0 items-center bg-[#1c2b3a]">
      {/* Left: Logo */}
      <div className="flex h-full items-center gap-2 pl-5 pr-8">
        <Image src="/logos/logo.svg" alt="Pyhron" width={80} height={22} className="h-[20px] w-auto brightness-0 invert" priority />
        <span className="text-[13px] font-bold text-white/40">ONE</span>
        <span className="text-white/25">◐</span>
      </div>

      {/* Center: Filter dropdown + Search — takes most of the width */}
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="flex w-full max-w-[680px] items-center overflow-hidden rounded border border-white/[0.18] bg-white">
          {/* Dropdown filter */}
          <button className="flex shrink-0 items-center gap-1 border-r border-[#e5e7eb] bg-[#f9fafb] px-3 py-[6px] text-[12px] font-medium text-[#374151]">
            All
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
          </button>
          {/* Search input area */}
          <button onClick={() => openPalette(true)} className="flex flex-1 items-center px-3 py-[6px] text-[12px] text-[#9ca3af]">
            Search
          </button>
          {/* Right icons: clear + search */}
          <div className="flex shrink-0 items-center gap-0.5 pr-2">
            <button className="p-1 text-[#9ca3af] hover:text-[#6b7280]">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
            <button className="p-1 text-[#9ca3af] hover:text-[#6b7280]">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
            </button>
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1 pr-4">
        <button className="flex items-center gap-1 rounded-full bg-[#166534] px-2.5 py-[3px] text-[10px] font-bold text-[#4ade80]">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10" /></svg>
          AskMSCI
          <span className="rounded bg-[#22c55e]/30 px-1 text-[8px] font-bold text-[#86efac]">BETA</span>
        </button>
        <button aria-label="Notifications" className="rounded p-1.5 text-white/50 hover:text-white/80">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" /></svg>
        </button>
        <button aria-label="Help" className="rounded p-1.5 text-white/50 hover:text-white/80">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
        </button>
        <div className="ml-1 flex h-[26px] w-[26px] items-center justify-center rounded-full bg-[#6366f1] text-[10px] font-bold text-white">
          VP
        </div>
      </div>
    </header>
  );
}
