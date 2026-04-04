'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { Search, X, Menu, ChevronDown, ChevronRight, ArrowRight } from 'lucide-react';

/* ---------- data ---------- */
interface NavColumn {
  heading: string;
  links: { label: string; href: string; desc?: string }[];
}
interface NavItem {
  label: string;
  href?: string;
  columns?: NavColumn[];
  featured?: { tag: string; title: string; href: string };
  bottomLink?: { label: string; href: string };
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Platform',
    columns: [
      {
        heading: 'Core',
        links: [
          { label: 'Dashboard', href: '/dashboard', desc: 'Portfolio overview & watchlists' },
          { label: 'Studio', href: '/studio', desc: 'Notebook-style research environment' },
          { label: 'Markets', href: '/markets', desc: 'Real-time market data & screener' },
        ],
      },
      {
        heading: 'Execution',
        links: [
          { label: 'Backtesting', href: '/studio/backtest', desc: 'Historical strategy simulation' },
          { label: 'Paper Trading', href: '/studio/paper', desc: 'Risk-free live simulation' },
          { label: 'Live Execution', href: '/studio/live', desc: 'Broker-connected trading' },
        ],
      },
    ],
    featured: { tag: 'New', title: 'ML Signal Engine v2 now available', href: '/research/signals' },
    bottomLink: { label: 'Explore the full platform', href: '/platform' },
  },
  {
    label: 'Data & Research',
    columns: [
      {
        heading: 'Data',
        links: [
          { label: 'Market Data', href: '/markets', desc: 'IDX equities, ETFs, bonds' },
          { label: 'Fundamental Data', href: '/research/fundamentals', desc: 'Financial statements & ratios' },
          { label: 'Alternative Data', href: '/research/alternative', desc: 'Sentiment, flow & macro' },
        ],
      },
      {
        heading: 'Research',
        links: [
          { label: 'Insights', href: '/research/articles', desc: 'Analyst reports & commentary' },
          { label: 'Signals', href: '/research/signals', desc: 'Quantitative factor signals' },
          { label: 'Methodology', href: '/methodology', desc: 'Our research framework' },
        ],
      },
    ],
    bottomLink: { label: 'Browse all research', href: '/research' },
  },
  {
    label: 'Indexes',
    columns: [
      {
        heading: 'Index Products',
        links: [
          { label: 'Pyhron Composite', href: '/indexes/composite', desc: 'Broad market benchmark' },
          { label: 'Factor Indexes', href: '/indexes/factors', desc: 'Smart-beta factor tilts' },
          { label: 'Custom Indexes', href: '/indexes/custom', desc: 'Build your own index' },
        ],
      },
    ],
    bottomLink: { label: 'View all indexes', href: '/indexes' },
  },
  { label: 'Pricing', href: '/pricing' },
  {
    label: 'About',
    columns: [
      {
        heading: 'Company',
        links: [
          { label: 'Our Story', href: '/about', desc: 'Mission & team' },
          { label: 'Contact', href: '/contact', desc: 'Get in touch' },
          { label: 'Blog', href: '/blog', desc: 'Updates & announcements' },
        ],
      },
    ],
  },
];

/* ---------- MegaDropdown ---------- */
function MegaDropdown({ item }: { item: NavItem }) {
  return (
    <div className="absolute left-0 top-full w-screen border-b border-[var(--border-default)] bg-[rgba(9,9,11,0.97)] backdrop-blur-xl">
      <div className="mx-auto grid max-w-7xl grid-cols-12 gap-8 px-8 py-8">
        {/* Columns */}
        <div className="col-span-8 grid grid-cols-2 gap-8">
          {item.columns?.map((col) => (
            <div key={col.heading}>
              <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-tertiary)]">
                {col.heading}
              </p>
              <ul className="space-y-1">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="group block rounded-md px-3 py-2 transition-colors hover:bg-white/5"
                    >
                      <span className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--accent-400)]">
                        {link.label}
                      </span>
                      {link.desc && (
                        <span className="mt-0.5 block text-xs text-[var(--text-tertiary)]">
                          {link.desc}
                        </span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Featured card */}
        {item.featured && (
          <div className="col-span-4">
            <Link
              href={item.featured.href}
              className="group block rounded-lg border border-[var(--border-default)] bg-white/[0.03] p-5 transition-colors hover:border-[var(--accent-500)]/40"
            >
              <span className="inline-block rounded-full bg-[var(--accent-500)]/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--accent-400)]">
                {item.featured.tag}
              </span>
              <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">
                {item.featured.title}
              </p>
              <span className="mt-2 inline-flex items-center gap-1 text-xs text-[var(--accent-400)]">
                Read more
                <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          </div>
        )}
      </div>

      {/* Bottom link */}
      {item.bottomLink && (
        <div className="border-t border-[var(--border-default)]">
          <div className="mx-auto max-w-7xl px-8 py-3">
            <Link
              href={item.bottomLink.href}
              className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent-400)] transition-colors hover:text-[var(--accent-300)]"
            >
              {item.bottomLink.label}
              <ChevronRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- MobileMenu ---------- */
function MobileMenu({ onClose }: { onClose: () => void }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[var(--surface-0)]">
      <div className="flex h-14 items-center justify-between px-6">
        <Link href="/" onClick={onClose} className="text-sm font-light tracking-[0.25em] text-[var(--text-primary)]">
          PYHRON
        </Link>
        <button onClick={onClose} aria-label="Close menu" className="text-[var(--text-secondary)]">
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="px-6 pb-8">
        {NAV_ITEMS.map((item) => (
          <div key={item.label} className="border-b border-[var(--border-default)]">
            {item.href ? (
              <Link
                href={item.href}
                onClick={onClose}
                className="block py-4 text-sm font-medium text-[var(--text-primary)]"
              >
                {item.label}
              </Link>
            ) : (
              <>
                <button
                  onClick={() => setExpanded(expanded === item.label ? null : item.label)}
                  className="flex w-full items-center justify-between py-4 text-sm font-medium text-[var(--text-primary)]"
                >
                  {item.label}
                  <ChevronDown
                    className={`h-4 w-4 text-[var(--text-tertiary)] transition-transform ${
                      expanded === item.label ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {expanded === item.label && (
                  <div className="pb-4 pl-4">
                    {item.columns?.map((col) => (
                      <div key={col.heading} className="mb-3">
                        <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-tertiary)]">
                          {col.heading}
                        </p>
                        {col.links.map((link) => (
                          <Link
                            key={link.href}
                            href={link.href}
                            onClick={onClose}
                            className="block py-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                          >
                            {link.label}
                          </Link>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}

        <div className="mt-6 space-y-3">
          <Link
            href="/login"
            onClick={onClose}
            className="block w-full rounded-lg border border-[var(--border-default)] py-3 text-center text-sm font-medium text-[var(--text-primary)]"
          >
            Client Log In
          </Link>
          <Link
            href="/register"
            onClick={onClose}
            className="block w-full rounded-lg bg-[var(--accent-500)] py-3 text-center text-sm font-medium text-white"
          >
            Get Started Free
          </Link>
        </div>
      </nav>
    </div>
  );
}

/* ---------- PublicNavbar ---------- */
export function PublicNavbar() {
  const [visible, setVisible] = useState(true);
  const [solid, setSolid] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navRef = useRef<HTMLElement>(null);
  const lastScrollY = useRef(0);

  // MSCI-style scroll: hide on scroll down, show on scroll up
  useEffect(() => {
    function onScroll() {
      const y = window.scrollY;
      const delta = y - lastScrollY.current;

      // Always show at very top
      if (y < 60) {
        setVisible(true);
        setSolid(false);
      } else {
        // Scrolling down → hide, scrolling up → show
        if (delta > 5) setVisible(false);
        else if (delta < -5) setVisible(true);
        setSolid(true);
      }

      lastScrollY.current = y;
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setActiveDropdown(null);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const openDropdown = useCallback((label: string) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setActiveDropdown(label);
  }, []);

  const scheduleClose = useCallback(() => {
    closeTimer.current = setTimeout(() => setActiveDropdown(null), 200);
  }, []);

  const hasBg = solid || !!activeDropdown;

  // Keep visible when dropdown is open
  const isVisible = visible || !!activeDropdown;

  return (
    <>
      <header
        ref={navRef}
        className={`fixed left-0 right-0 z-50 transition-all duration-300 ${
          isVisible ? 'top-0' : '-top-full'
        } ${
          hasBg
            ? 'border-b border-[var(--border-default)] bg-[rgba(9,9,11,0.95)] backdrop-blur-xl backdrop-saturate-150 shadow-lg shadow-black/10'
            : 'bg-transparent'
        }`}
      >
        {/* Utility bar */}
        <div className="hidden border-b border-white/[0.06] lg:block">
          <div className="mx-auto flex h-8 max-w-7xl items-center justify-end gap-4 px-8 text-[11px] text-[var(--text-tertiary)]">
            <Link href="/contact" className="transition-colors hover:text-[var(--text-secondary)]">
              Support
            </Link>
            <span className="text-white/10">|</span>
            <Link href="/login" className="transition-colors hover:text-[var(--text-secondary)]">
              Client Log In
            </Link>
          </div>
        </div>

        {/* Main nav */}
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6 lg:px-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5 text-[var(--accent-400)]"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <circle cx="12" cy="12" r="10" />
              <ellipse cx="12" cy="12" rx="4" ry="10" />
              <path d="M2 12h20" />
            </svg>
            <span className="text-sm font-light tracking-[0.25em] text-[var(--text-primary)]">
              PYHRON
            </span>
          </Link>

          {/* Desktop nav items */}
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Main navigation">
            {NAV_ITEMS.map((item) =>
              item.href ? (
                <Link
                  key={item.label}
                  href={item.href}
                  className="rounded-md px-3 py-1.5 text-[13px] font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
                >
                  {item.label}
                </Link>
              ) : (
                <div
                  key={item.label}
                  onMouseEnter={() => openDropdown(item.label)}
                  onMouseLeave={scheduleClose}
                >
                  <button
                    className={`inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors ${
                      activeDropdown === item.label
                        ? 'text-[var(--text-primary)]'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                    onClick={() =>
                      setActiveDropdown(activeDropdown === item.label ? null : item.label)
                    }
                  >
                    {item.label}
                    <ChevronDown
                      className={`h-3 w-3 transition-transform ${
                        activeDropdown === item.label ? 'rotate-180' : ''
                      }`}
                    />
                  </button>
                  {activeDropdown === item.label && <MegaDropdown item={item} />}
                </div>
              ),
            )}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <button
              aria-label="Search"
              className="text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
            >
              <Search className="h-4 w-4" strokeWidth={1.5} />
            </button>
            <Link
              href="/dashboard"
              className="hidden rounded-full bg-[var(--accent-500)] px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-600)] lg:inline-flex lg:items-center lg:gap-1"
            >
              Launch Terminal
              <span aria-hidden="true" className="ml-0.5">&rarr;</span>
            </Link>
            <button
              aria-label="Open menu"
              onClick={() => setMobileOpen(true)}
              className="text-[var(--text-secondary)] lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* No spacer — content starts at top, header overlays it */}

      {/* Mobile menu */}
      {mobileOpen && <MobileMenu onClose={() => setMobileOpen(false)} />}
    </>
  );
}
