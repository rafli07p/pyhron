'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Search, X, Menu, ChevronDown } from 'lucide-react';

/* ═══ NAV DATA ═══ */
interface NavColumn { title?: string; items: { label: string; href: string }[] }
interface NavItem {
  label: string;
  href?: string;
  columns?: NavColumn[];
  featured?: { type: string; title: string; desc: string; cta: string; ctaHref: string };
  footer?: { label: string; href: string };
}

const NAV: NavItem[] = [
  {
    label: 'Data & Analytics',
    columns: [
      { title: 'By topic', items: [
        { label: 'Market Data', href: '/data/catalog' },
        { label: 'Factor Analysis', href: '/studio/factors' },
        { label: 'Fundamental Data', href: '/data/catalog' },
        { label: 'Technical Signals', href: '/research/signals' },
        { label: 'ML-Driven Signals', href: '/research/signals' },
        { label: 'Macro & Economic', href: '/data/catalog' },
      ] },
      { title: 'By asset class', items: [
        { label: 'Equities', href: '/markets' },
        { label: 'Fixed Income', href: '/data/catalog' },
        { label: 'Money Market', href: '/data/catalog' },
        { label: 'Sukuk', href: '/data/catalog' },
      ] },
    ],
    featured: { type: 'Featured product', title: 'IDX Market Screener', desc: 'Filter and rank 800+ IDX instruments by fundamental and technical criteria.', cta: 'Explore now', ctaHref: '/markets' },
    footer: { label: 'View all data products', href: '/data' },
  },
  {
    label: 'Indexes',
    columns: [
      { title: 'Index categories', items: [
        { label: 'Market Cap', href: '/indexes' },
        { label: 'Factors', href: '/indexes' },
        { label: 'Sector', href: '/indexes' },
        { label: 'Shariah-Compliant', href: '/indexes' },
        { label: 'Custom', href: '/indexes' },
      ] },
      { title: 'Index resources', items: [
        { label: 'Index Constituents', href: '/indexes' },
        { label: 'Methodologies', href: '/methodology' },
        { label: 'Rebalancing Calendar', href: '/indexes' },
      ] },
    ],
    featured: { type: 'Featured index', title: 'IHSG Composite Index', desc: 'Track Indonesia\'s primary market benchmark in real time.', cta: 'View index', ctaHref: '/indexes' },
    footer: { label: 'View all indexes', href: '/indexes' },
  },
  {
    label: 'Research & Insights',
    columns: [
      { title: 'By theme', items: [
        { label: 'Quantitative Strategies', href: '/research' },
        { label: 'Machine Learning', href: '/research' },
        { label: 'Risk Management', href: '/research' },
        { label: 'Market Microstructure', href: '/research' },
        { label: 'Macro & Rates', href: '/research' },
      ] },
      { title: 'By asset class', items: [
        { label: 'Equities', href: '/research' },
        { label: 'Fixed Income', href: '/research' },
        { label: 'Multi-Asset', href: '/research' },
      ] },
    ],
    featured: { type: 'Featured research', title: 'IDX Factor Investing 2026', desc: 'How momentum, value, and quality factors perform in Indonesia\'s market.', cta: 'Read the report', ctaHref: '/research' },
    footer: { label: 'View all insights', href: '/research' },
  },
  {
    label: 'Discover Pyhron',
    columns: [
      { title: 'Who we are', items: [
        { label: 'About Us', href: '/about' },
        { label: 'Methodology', href: '/methodology' },
        { label: 'Contact', href: '/contact' },
      ] },
      { title: 'News & updates', items: [
        { label: 'Changelog', href: '/changelog' },
        { label: 'Status', href: '/status' },
      ] },
      { title: 'Resources', items: [
        { label: 'API Documentation', href: '/data/api' },
        { label: 'Help Center', href: '/contact' },
      ] },
    ],
  },
  { label: 'Pricing', href: '/pricing' },
];

/* ═══ MEGA DROPDOWN — FIXED FULL-WIDTH ═══ */
function MegaDropdown({ item, onClose }: { item: NavItem; onClose: () => void }) {
  return (
    <div className="fixed inset-x-0 top-[88px] z-50 bg-white shadow-xl">
      <div className="mx-auto flex max-w-[1200px] gap-16 px-8 py-10">
        <div className="flex flex-1 gap-12">
          {item.columns?.map((col, i) => (
            <div key={i} className="min-w-[180px]">
              {col.title && <h3 className="mb-5 text-[13px] font-normal text-black/35">{col.title}</h3>}
              <ul className="space-y-3.5">
                {col.items.map((link) => (
                  <li key={link.label}>
                    <Link href={link.href} onClick={onClose} className="text-[14px] text-black/65 transition-colors hover:text-black">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        {item.featured && (
          <div className="w-[260px] shrink-0 border-l border-black/[0.08] pl-12">
            <p className="mb-3 text-[12px] font-medium text-[#2563eb]">{item.featured.type}</p>
            <h4 className="mb-2 text-[16px] font-semibold leading-snug text-black">{item.featured.title}</h4>
            <p className="mb-5 text-[13px] leading-relaxed text-black/45">{item.featured.desc}</p>
            <Link href={item.featured.ctaHref} onClick={onClose} className="inline-flex h-9 items-center rounded-full border border-black/15 px-5 text-[13px] text-black/60 transition-colors hover:border-black/30 hover:text-black">
              {item.featured.cta}
            </Link>
          </div>
        )}
      </div>
      {item.footer && (
        <div className="border-t border-black/[0.06]">
          <div className="mx-auto max-w-[1200px] px-8 py-5">
            <Link href={item.footer.href} onClick={onClose} className="text-[13px] text-black/40 underline underline-offset-4 decoration-black/15 transition-colors hover:text-black/70 hover:decoration-black/40">
              {item.footer.label}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══ MOBILE MENU ═══ */
function MobileMenu({ onClose }: { onClose: () => void }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="fixed inset-0 z-[55] overflow-y-auto bg-white">
      <div className="flex h-14 items-center justify-between px-6">
        <Link href="/" onClick={onClose} className="text-[15px] font-semibold tracking-[0.18em] text-black">PYHRON</Link>
        <button onClick={onClose} aria-label="Close menu" className="text-black/40"><X className="h-5 w-5" /></button>
      </div>
      <nav className="px-6 pb-8">
        {NAV.map((item) => (
          <div key={item.label} className="border-b border-black/[0.06]">
            {item.href ? (
              <Link href={item.href} onClick={onClose} className="block py-4 text-sm font-medium text-black/80">{item.label}</Link>
            ) : (
              <>
                <button onClick={() => setExpanded(expanded === item.label ? null : item.label)} className="flex w-full items-center justify-between py-4 text-sm font-medium text-black/80">
                  {item.label}
                  <ChevronDown className={`h-4 w-4 text-black/30 transition-transform ${expanded === item.label ? 'rotate-180' : ''}`} />
                </button>
                {expanded === item.label && (
                  <div className="pb-4 pl-4">
                    {item.columns?.map((col, i) => (
                      <div key={i} className="mb-3">
                        {col.title && <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-black/25">{col.title}</p>}
                        {col.items.map((link) => (
                          <Link key={link.label} href={link.href} onClick={onClose} className="block py-1.5 text-sm text-black/50 hover:text-black">{link.label}</Link>
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
          <a href="/dashboard" target="_blank" rel="noopener noreferrer" onClick={onClose} className="block w-full rounded-lg bg-[#2563eb] py-3 text-center text-sm font-medium text-white">Launch Terminal</a>
          <Link href="/contact" onClick={onClose} className="block w-full rounded-lg border border-black/10 py-3 text-center text-sm text-black/60">Get in touch</Link>
        </div>
      </nav>
    </div>
  );
}

/* ═══ CLIENT LOGIN DROPDOWN ═══ */
function ClientLoginDropdown({ dark }: { dark: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className={`px-3 text-[12px] transition-colors ${dark ? 'text-white/50 hover:text-white/80' : 'text-black/40 hover:text-black/70'}`}>
        Client Log In
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-8 z-50 w-[260px] rounded-lg border border-black/10 bg-white py-3 shadow-2xl">
            <p className="px-4 pb-2 text-[11px] font-medium text-black/30">Select a site</p>
            <a href="/login" onClick={() => setOpen(false)} className="flex items-center border-l-4 border-transparent px-4 py-3 text-[14px] font-medium text-black/80 transition-colors hover:border-[#2563eb] hover:bg-black/[0.03]">
              Pyhron ONE
            </a>
          </div>
        </>
      )}
    </div>
  );
}

/* ═══ PUBLIC NAVBAR ═══ */
export function PublicNavbar() {
  const [scrollState, setScrollState] = useState<'top' | 'hidden' | 'visible'>('top');
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const lastScrollY = useRef(0);

  useEffect(() => {
    function onScroll() {
      const y = window.scrollY;
      const down = y > lastScrollY.current;
      if (y < 10) setScrollState('top');
      else if (down && y > 100) setScrollState('hidden');
      else if (!down) setScrollState('visible');
      lastScrollY.current = y;
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (
        navRef.current && !navRef.current.contains(e.target as Node) &&
        (!dropdownRef.current || !dropdownRef.current.contains(e.target as Node))
      ) {
        setActiveDropdown(null);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  // Dark text on hero (transparent bg), light text when scrolled (white bg)
  const dark = scrollState === 'top' && !activeDropdown;
  const closeDropdown = () => setActiveDropdown(null);

  return (
    <>
      <header
        ref={navRef}
        className={`fixed left-0 right-0 z-50 transition-transform duration-300 ${
          scrollState === 'hidden' && !activeDropdown ? '-translate-y-full' : 'translate-y-0'
        } ${
          dark ? 'bg-transparent' : 'bg-white shadow-sm'
        }`}
      >
        {/* Utility bar — NO border */}
        <div className="hidden lg:block">
          <div className="mx-auto flex h-7 max-w-[1400px] items-center justify-end gap-0 px-8">
            <Link href="/contact" className={`px-3 text-[12px] transition-colors ${dark ? 'text-white/50 hover:text-white/80' : 'text-black/40 hover:text-black/70'}`}>
              Support
            </Link>
            <span className={dark ? 'text-white/15' : 'text-black/15'}>|</span>
            <ClientLoginDropdown dark={dark} />
          </div>
        </div>

        {/* Main nav */}
        <div className="relative mx-auto flex h-[60px] max-w-[1400px] items-center justify-between px-6 lg:px-8">
          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            <svg viewBox="0 0 24 24" className={`h-6 w-6 ${dark ? 'text-white/50' : 'text-black/30'}`} fill="none" stroke="currentColor" strokeWidth={1.2}>
              <circle cx="12" cy="12" r="10" /><ellipse cx="12" cy="12" rx="4" ry="10" /><path d="M2 12h20" />
            </svg>
            <span className={`text-[17px] font-semibold tracking-[0.18em] ${dark ? 'text-white' : 'text-black'}`}>PYHRON</span>
          </Link>

          {/* Desktop nav — CLICK to open dropdown */}
          <nav className="ml-10 hidden items-center gap-0.5 lg:flex" aria-label="Main navigation">
            {NAV.map((item) =>
              item.href ? (
                <Link key={item.label} href={item.href} className={`flex h-[60px] items-center px-4 text-[14px] transition-colors ${dark ? 'text-white/70 hover:text-white' : 'text-black/60 hover:text-black'}`}>
                  {item.label}
                </Link>
              ) : (
                <div key={item.label} className="relative">
                  <button
                    onClick={() => setActiveDropdown(activeDropdown === item.label ? null : item.label)}
                    className={`flex h-[60px] items-center gap-1.5 px-4 text-[14px] transition-colors ${
                      activeDropdown === item.label
                        ? (dark ? 'text-white' : 'text-black')
                        : (dark ? 'text-white/70 hover:text-white/90' : 'text-black/60 hover:text-black/80')
                    }`}
                  >
                    {item.label}
                    <ChevronDown className={`h-3.5 w-3.5 opacity-50 transition-transform ${activeDropdown === item.label ? 'rotate-180' : ''}`} />
                  </button>
                  {activeDropdown === item.label && (
                    <div className="absolute bottom-0 left-4 right-4 h-[3px] bg-[#2563eb]" />
                  )}
                </div>
              ),
            )}
          </nav>

          <div className="flex items-center gap-3">
            <div className={`hidden h-9 w-[160px] items-center gap-2 rounded-full border px-4 text-[13px] lg:flex ${dark ? 'border-white/15 text-white/40' : 'border-black/15 text-black/40'}`}>
              <Search className="h-4 w-4" />
              <span>Search</span>
            </div>
            <Link href="/contact" className="hidden h-9 items-center rounded-full bg-[#2563eb] px-6 text-[13px] font-medium text-white transition-colors hover:bg-[#1d4ed8] lg:inline-flex">
              Get in touch
            </Link>
            <button aria-label="Open menu" onClick={() => setMobileOpen(true)} className={`lg:hidden ${dark ? 'text-white/60' : 'text-black/60'}`}><Menu className="h-5 w-5" /></button>
          </div>
        </div>
      </header>

      {/* Full-width mega dropdown rendered OUTSIDE the header to use fixed positioning */}
      <div ref={dropdownRef}>
        {activeDropdown && NAV.find((n) => n.label === activeDropdown && n.columns) && (
          <MegaDropdown item={NAV.find((n) => n.label === activeDropdown)!} onClose={closeDropdown} />
        )}
      </div>

      {mobileOpen && <MobileMenu onClose={() => setMobileOpen(false)} />}
    </>
  );
}
