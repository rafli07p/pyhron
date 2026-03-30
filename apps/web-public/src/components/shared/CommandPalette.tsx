'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Fuse from 'fuse.js';
import { Search, FileText, BarChart3, X } from 'lucide-react';
import { mockArticles } from '@/lib/mock/data/research';
import { mockInstruments } from '@/lib/mock/data/instruments';

interface SearchResult {
  title: string;
  href: string;
  section: 'Pages' | 'Research' | 'Stocks';
}

const staticPages: SearchResult[] = [
  { title: 'Home', href: '/', section: 'Pages' },
  { title: 'Research', href: '/research', section: 'Pages' },
  { title: 'Stock Screener', href: '/data/screener', section: 'Pages' },
  { title: 'Index Dashboard', href: '/data/indices', section: 'Pages' },
  { title: 'Pricing', href: '/pricing', section: 'Pages' },
  { title: 'About', href: '/about', section: 'Pages' },
  { title: 'Contact', href: '/contact', section: 'Pages' },
  { title: 'API Documentation', href: '/developers/api', section: 'Pages' },
  { title: 'Dashboard', href: '/dashboard/overview', section: 'Pages' },
];

const allResults: SearchResult[] = [
  ...staticPages,
  ...mockArticles.map((a) => ({
    title: a.title,
    href: `/research/${a.slug}`,
    section: 'Research' as const,
  })),
  ...mockInstruments.slice(0, 30).map((i) => ({
    title: `${i.symbol} - ${i.name}`,
    href: `/data/screener?symbol=${i.symbol}`,
    section: 'Stocks' as const,
  })),
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const fuse = useMemo(
    () => new Fuse(allResults, { keys: ['title'], threshold: 0.4 }),
    [],
  );

  const results = useMemo(() => {
    if (!query) return allResults.slice(0, 24);
    return fuse.search(query, { limit: 24 }).map((r) => r.item);
  }, [query, fuse]);

  const grouped = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {};
    for (const r of results) {
      if (!groups[r.section]) groups[r.section] = [];
      if (groups[r.section].length < 8) groups[r.section].push(r);
    }
    return groups;
  }, [results]);

  const flatResults = useMemo(() => Object.values(grouped).flat(), [grouped]);

  const handleSelect = useCallback(
    (result: SearchResult) => {
      setOpen(false);
      setQuery('');
      router.push(result.href);
    },
    [router],
  );

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyNav = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, flatResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && flatResults[selectedIndex]) {
      handleSelect(flatResults[selectedIndex]);
    }
  };

  if (!open) return null;

  const sectionIcons: Record<string, React.ReactNode> = {
    Pages: <FileText className="h-3.5 w-3.5" />,
    Research: <Search className="h-3.5 w-3.5" />,
    Stocks: <BarChart3 className="h-3.5 w-3.5" />,
  };

  let flatIndex = 0;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-lg rounded-lg border border-border bg-bg-primary shadow-2xl">
        <div className="flex items-center border-b border-border px-4">
          <Search className="h-4 w-4 text-text-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyNav}
            placeholder="Search pages, research, stocks..."
            className="flex-1 bg-transparent px-3 py-3 text-sm text-text-primary outline-none placeholder:text-text-muted"
          />
          <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-primary">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {Object.entries(grouped).map(([section, items]) => (
            <div key={section} className="mb-2">
              <p className="flex items-center gap-1.5 px-2 py-1 text-xs font-semibold uppercase tracking-wider text-text-muted">
                {sectionIcons[section]} {section}
              </p>
              {items.map((item) => {
                const idx = flatIndex++;
                return (
                  <button
                    key={item.href}
                    onClick={() => handleSelect(item)}
                    className={`flex w-full items-center rounded-md px-3 py-2 text-sm text-left transition-colors ${
                      selectedIndex === idx ? 'bg-accent-500/10 text-accent-500' : 'text-text-secondary hover:bg-bg-tertiary'
                    }`}
                  >
                    {item.title}
                  </button>
                );
              })}
            </div>
          ))}
          {flatResults.length === 0 && (
            <p className="px-3 py-4 text-center text-sm text-text-muted">No results found</p>
          )}
        </div>
      </div>
    </div>
  );
}
