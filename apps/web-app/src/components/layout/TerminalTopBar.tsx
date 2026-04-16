'use client';

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';

const FILTER_OPTIONS = ['All', 'Index', 'Reports', 'Portfolios', 'Companies', 'Apps', 'Research', 'Data', 'APIs', 'Videos', 'Securities'];

export function TerminalTopBar() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filter, setFilter] = useState('All');
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const filterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (searchOpen && inputRef.current) inputRef.current.focus();
  }, [searchOpen]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setSearchOpen(false);
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) setFilterOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const searchHistory = ['LQ45 Indonesia', 'IDX Composite', 'BBCA'];

  return (
    <header className="sticky top-0 z-40 flex h-[48px] shrink-0 items-center bg-[#0a1628]">
      {/* Logo */}
      <div className="flex h-full shrink-0 items-center pl-5 pr-8">
        <Image src="/logos/logo.svg" alt="Pyhron ONE" width={120} height={30} className="h-[24px] w-auto brightness-0 invert" priority />
      </div>

      {/* Center: Filter + Search */}
      <div ref={searchRef} className="relative flex flex-1 items-center justify-center px-4">
        <div className="flex w-full max-w-[800px] items-stretch rounded-[4px] border-2 border-[#2563eb]/60 bg-white">
          {/* Filter dropdown */}
          <div ref={filterRef} className="relative">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className="flex h-full items-center gap-1 border-r border-[#e5e7eb] bg-[#f8fafc] px-3 text-[13px] font-medium text-[#1e3a5f]"
            >
              {filter}
              <svg width="10" height="10" viewBox="0 0 20 20" fill="#64748b"><path d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" /></svg>
            </button>
            {filterOpen && (
              <div className="absolute left-0 top-full z-50 mt-[2px] w-[180px] rounded-b border border-[#e5e7eb] bg-white py-1 shadow-lg">
                {FILTER_OPTIONS.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => { setFilter(opt); setFilterOpen(false); }}
                    className={`block w-full px-4 py-2 text-left text-[13px] transition-colors hover:bg-[#f1f5f9] ${filter === opt ? 'font-semibold text-[#1e3a5f]' : 'text-[#374151]'}`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Search input */}
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search"
            className="flex-1 bg-transparent px-3 py-[7px] text-[13px] text-[#111827] outline-none placeholder:text-[#9ca3af]"
          />

          {/* Magnifier button */}
          <button
            onClick={() => { if (query) console.log('Search:', query); }}
            className="flex shrink-0 items-center px-3 text-[#6366f1] hover:text-[#4f46e5]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
          </button>
        </div>

        {/* Search history dropdown */}
        {searchOpen && (
          <div className="absolute left-1/2 top-[44px] z-50 w-full max-w-[800px] -translate-x-1/2 border border-[#e5e7eb] bg-white py-2 shadow-lg">
            <p className="px-4 pb-1.5 text-[12px] font-bold text-[#111827]">Search History</p>
            {searchHistory.map((s) => (
              <button key={s} onClick={() => { setQuery(s); setSearchOpen(false); }} className="flex w-full items-center gap-2.5 px-4 py-2 text-[13px] text-[#374151] hover:bg-[#f1f5f9]">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-1 pr-4">
        <button className="flex items-center gap-1.5 rounded-full bg-[#14532d] px-3 py-[4px] text-[11px] font-bold text-[#4ade80]">
          <svg width="8" height="8" viewBox="0 0 24 24" fill="#4ade80"><circle cx="12" cy="12" r="10" /></svg>
          AskPyhron
          <span className="rounded bg-[#22c55e]/30 px-1 text-[9px] text-[#86efac]">BETA</span>
        </button>
        <button aria-label="Notifications" className="rounded p-2 text-white/50 hover:text-white/80">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" /></svg>
        </button>
        <button aria-label="Help" className="rounded p-2 text-white/50 hover:text-white/80">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
        </button>
        <div className="ml-1 flex h-[30px] w-[30px] items-center justify-center rounded-full bg-[#6366f1] text-[11px] font-bold text-white">
          RP
        </div>
      </div>
    </header>
  );
}
