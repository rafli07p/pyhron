'use client';

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';

export function TerminalTopBar() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (searchOpen && inputRef.current) inputRef.current.focus();
  }, [searchOpen]);

  useEffect(() => {
    if (!searchOpen) return;
    function handleClick(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [searchOpen]);

  const searchHistory = ['LQ45 Indonesia', 'IDX Composite', 'BBCA'];

  return (
    <header className="sticky top-0 z-40 flex h-[42px] shrink-0 items-center bg-[#1a2d42]">
      {/* Logo */}
      <div className="flex h-full shrink-0 items-center pl-4 pr-6">
        <Image src="/logos/logo.svg" alt="Pyhron ONE" width={100} height={28} className="h-[22px] w-auto brightness-0 invert" priority />
      </div>

      {/* Center: Filter + Search */}
      <div ref={searchRef} className="relative flex flex-1 items-center justify-center px-4">
        <div className="flex w-full max-w-[800px] items-center rounded-[3px] border border-white/20 bg-white">
          <button className="flex shrink-0 items-center gap-1 border-r border-[#d1d5db] px-3 py-[5px] text-[12px] font-medium text-[#1f2937]">
            All
            <svg width="10" height="10" viewBox="0 0 20 20" fill="#6b7280"><path d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" /></svg>
          </button>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search"
            className="flex-1 bg-transparent px-3 py-[5px] text-[12px] text-[#111827] outline-none placeholder:text-[#9ca3af]"
          />
          <button className="shrink-0 px-2 py-1 text-[#6366f1]">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
          </button>
        </div>

        {/* Search dropdown */}
        {searchOpen && (
          <div className="absolute left-1/2 top-[38px] w-full max-w-[800px] -translate-x-1/2 rounded-b-md border border-t-0 border-[#e5e7eb] bg-white py-2 shadow-lg">
            <p className="px-4 pb-1 text-[11px] font-bold text-[#111827]">Search History</p>
            {searchHistory.map((s) => (
              <button key={s} onClick={() => { setQuery(s); setSearchOpen(false); }} className="flex w-full items-center gap-2.5 px-4 py-1.5 text-[13px] text-[#374151] hover:bg-[#f3f4f6]">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-0.5 pr-4">
        <button className="flex items-center gap-1 rounded-full bg-[#14532d] px-2 py-[2px] text-[10px] font-bold text-[#4ade80]">
          <svg width="8" height="8" viewBox="0 0 24 24" fill="#4ade80"><circle cx="12" cy="12" r="10" /></svg>
          AskMSCI
          <span className="rounded bg-[#22c55e]/30 px-1 text-[8px] text-[#86efac]">BETA</span>
        </button>
        <button className="rounded p-1.5 text-white/45 hover:text-white/75">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" /></svg>
        </button>
        <button className="rounded p-1.5 text-white/45 hover:text-white/75">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
        </button>
        <div className="ml-1 flex h-[26px] w-[26px] items-center justify-center rounded-full bg-[#6366f1] text-[9px] font-bold text-white">
          RP
        </div>
      </div>
    </header>
  );
}
