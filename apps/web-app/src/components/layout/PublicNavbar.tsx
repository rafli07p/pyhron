'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { Search, X, Menu, ChevronDown } from 'lucide-react';

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
                    { label: 'Market Data', href: '/data/market-data' },
                    { label: 'Factor Analysis', href: '/data/factors' },
                    { label: 'Fundamental Data', href: '/data/fundamentals' },
                    { label: 'Technical Signals', href: '/data/technicals' },
                    { label: 'ML-Driven Signals', href: '/data/ml-signals' },
                    { label: 'Macro & Economic', href: '/data/macro' },
                ] },
            { title: 'By asset class', items: [
                    { label: 'Equities', href: '/data/equities' },
                    { label: 'Fixed Income', href: '/data/fixed-income' },
                    { label: 'Money Market', href: '/data' },
                    { label: 'Sukuk', href: '/data' },
                ] },
        ],
        featured: { type: 'Featured product', title: 'IDX Market Screener', desc: 'Filter and rank 800+ IDX instruments by fundamental and technical criteria.', cta: 'Explore now', ctaHref: '/data/equities' },
        footer: { label: 'View all data products', href: '/data' },
    },
    {
        label: 'Indexes',
        columns: [
            { title: 'Index categories', items: [
                    { label: 'Market Cap', href: '/indexes/market-cap' },
                    { label: 'Factors', href: '/indexes/factors' },
                    { label: 'Sector', href: '/indexes/sector' },
                    { label: 'Shariah-Compliant', href: '/indexes/shariah' },
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
                    { label: 'Quantitative Strategies', href: '/research-and-insights/quant' },
                    { label: 'Machine Learning', href: '/research-and-insights/ml' },
                    { label: 'Risk Management', href: '/research-and-insights/risk' },
                    { label: 'Market Microstructure', href: '/research-and-insights' },
                    { label: 'Macro & Rates', href: '/research-and-insights/macro' },
                ] },
            { title: 'By asset class', items: [
                    { label: 'Equities', href: '/research-and-insights/equities' },
                    { label: 'Fixed Income', href: '/research-and-insights/fixed-income' },
                    { label: 'Multi-Asset', href: '/research-and-insights/multi-asset' },
                ] },
        ],
        featured: { type: 'Featured research', title: 'IDX Factor Investing 2026', desc: 'How momentum, value, and quality factors perform in Indonesia\'s market.', cta: 'Read the report', ctaHref: '/research-and-insights' },
        footer: { label: 'View all insights', href: '/research-and-insights' },
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
                    { label: 'API Documentation', href: '/methodology' },
                    { label: 'Help Center', href: '/contact' },
                ] },
        ],
    },
    { label: 'Pricing', href: '/pricing' },
];

function MegaDropdown({ item, onClose }: { item: NavItem; onClose: () => void }) {
    return (
        <div className="fixed inset-x-0 top-[88px] z-50 bg-white shadow-xl">
            <div className="mx-auto flex max-w-[1400px] gap-16 px-8 py-10">
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
                    <div className="mx-auto max-w-[1400px] px-8 py-5">
                        <Link href={item.footer.href} onClick={onClose} className="text-[13px] text-black/40 underline underline-offset-4 decoration-black/15 transition-colors hover:text-black/70 hover:decoration-black/40">
                            {item.footer.label}
                        </Link>
                    </div>
                </div>
            )}
        </div>
    );
}

function MobileMenu({ onClose }: { onClose: () => void }) {
    const [expanded, setExpanded] = useState<string | null>(null);
    return (
        <div className="fixed inset-0 z-[55] overflow-y-auto bg-white">
            <div className="flex h-14 items-center justify-between px-6">
                <Link href="/" onClick={onClose}>
                    <Image src="/logos/logo.svg" alt="Pyhron" width={100} height={27} className="h-7 w-auto" />
                </Link>
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
                    <Link href="/register" onClick={onClose} className="block w-full rounded-lg bg-[#2563eb] py-3 text-center text-sm font-medium text-white">Get Started Free</Link>
                    <Link href="/contact" onClick={onClose} className="block w-full rounded-lg border border-black/10 py-3 text-center text-sm text-black/60">Get in touch</Link>
                </div>
            </nav>
        </div>
    );
}

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

/** Search — MSCI style: hides nav items when expanded, logo + search + button visible */
function ExpandableSearch({ searchOpen, setSearchOpen }: { searchOpen: boolean; setSearchOpen: (v: boolean) => void }) {
    const [query, setQuery] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (searchOpen && inputRef.current) inputRef.current.focus();
    }, [searchOpen]);

    useEffect(() => {
        if (!searchOpen) return;
        function handleClick(e: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setSearchOpen(false);
                setQuery('');
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [searchOpen, setSearchOpen]);

    const popular = ['BBCA', 'IHSG', 'momentum', 'factor', 'screener'];

    if (!searchOpen) {
        return (
            <button
                onClick={() => setSearchOpen(true)}
                className="hidden h-11 w-[160px] items-center gap-2 rounded-full border border-black/15 px-5 text-[14px] text-black/40 transition-colors hover:border-black/25 lg:flex"
            >
                <Search className="h-4 w-4 shrink-0" />
                <span>Search</span>
            </button>
        );
    }

    return (
        <div ref={containerRef} className="relative hidden flex-1 lg:block">
            <div className="flex h-11 items-center gap-2 rounded-full border-2 border-[#2563eb] bg-white px-5">
                <Search className="h-4 w-4 shrink-0 text-black/30" />
                <input
                    ref={inputRef}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && query) window.location.href = `/search?q=${encodeURIComponent(query)}`;
                        if (e.key === 'Escape') { setSearchOpen(false); setQuery(''); }
                    }}
                    placeholder="Search"
                    className="flex-1 bg-transparent text-[14px] text-black outline-none placeholder:text-black/40"
                />
                {query && <button onClick={() => setQuery('')} className="text-[13px] text-black/30 hover:text-black/60">Clear</button>}
                <button onClick={() => { setSearchOpen(false); setQuery(''); }} className="text-black/30 hover:text-black/60"><X className="h-4 w-4" /></button>
            </div>
            <div className="absolute left-0 right-0 top-[48px] rounded-lg border border-black/[0.06] bg-white py-4 shadow-xl">
                {!query ? (
                    <>
                        <p className="mb-2 px-5 text-[12px] text-black/30">Popular Searches</p>
                        {popular.map((s) => (
                            <button key={s} onClick={() => setQuery(s)} className="flex w-full items-center gap-3 px-5 py-2.5 text-[14px] text-black/60 transition-colors hover:bg-black/[0.02]">
                                <Search className="h-3.5 w-3.5 text-black/20" />
                                {s}
                            </button>
                        ))}
                    </>
                ) : (
                    <p className="px-5 py-3 text-[13px] text-black/40">Press Enter to search for &ldquo;{query}&rdquo;</p>
                )}
            </div>
        </div>
    );
}

export function PublicNavbar() {
    const pathname = usePathname();
    const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
    const [hoveredLabel, setHoveredLabel] = useState<string | null>(null);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [searchOpen, setSearchOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const [hidden, setHidden] = useState(false);
    const navRef = useRef<HTMLElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const [prevPathname, setPrevPathname] = useState(pathname);
    if (prevPathname !== pathname) {
        setPrevPathname(pathname);
        setActiveDropdown(null);
        setHoveredLabel(null);
        setMobileOpen(false);
        setSearchOpen(false);
    }

    const toggleDropdown = (label: string) => {
        setActiveDropdown((prev) => (prev === label ? null : label));
    };

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

    // Scroll: transparent at top, instant dark bg when below threshold.
    // Slide up to hide on scroll down, slide down to show on scroll up.
    // Instant transparent when back at top (no fade).
    useEffect(() => {
        let lastY = typeof window !== 'undefined' ? window.scrollY : 0;
        let ticking = false;
        const THRESHOLD = 10;
        const DELTA = 6;

        function update() {
            const y = window.scrollY;
            const dy = y - lastY;

            setScrolled(y > THRESHOLD);

            if (y <= THRESHOLD) {
                setHidden(false);
            } else if (Math.abs(dy) > DELTA) {
                if (dy > 0) {
                    setHidden(true);
                    setActiveDropdown(null);
                } else {
                    setHidden(false);
                }
            }

            lastY = y;
            ticking = false;
        }

        function onScroll() {
            if (!ticking) {
                window.requestAnimationFrame(update);
                ticking = true;
            }
        }

        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    const closeDropdown = () => setActiveDropdown(null);

    const dark = scrolled;
    const textColor = dark ? 'text-white/70 hover:text-white' : 'text-black/70 hover:text-black';
    const textActive = dark ? 'text-white' : 'text-black';
    const underlineColor = dark ? 'bg-white' : 'bg-black';

    return (
        <>
            <header
                ref={navRef}
                style={{
                    transform: hidden ? 'translateY(-100%)' : 'translateY(0)',
                    transition: 'transform 0.3s ease-out',
                    backgroundColor: scrolled ? '#0a0e1a' : 'transparent',
                }}
                className="fixed left-0 right-0 z-50"
            >
                {/* Utility bar */}
                <div className="hidden lg:block">
                    <div className="mx-auto flex h-7 max-w-[1400px] items-center justify-end gap-0 px-8">
                        <Link href="/contact" className={`px-3 text-[12px] transition-colors ${dark ? 'text-white/40 hover:text-white/70' : 'text-black/40 hover:text-black/70'}`}>
                            Support
                        </Link>
                        <span className={dark ? 'text-white/15' : 'text-black/15'}>|</span>
                        <ClientLoginDropdown dark={dark} />
                    </div>
                </div>

                {/* Main nav bar */}
                <div className={`relative mx-auto flex h-[60px] max-w-[1400px] items-center justify-between border-b border-dashed px-6 lg:px-8 ${
                    dark ? 'border-white/10' : 'border-black/[0.08]'
                }`}>
                    <Link href="/" className="flex shrink-0 items-center">
                        <Image
                            src={dark ? '/logos/logo-dark.svg' : '/logos/logo.svg'}
                            alt="Pyhron"
                            width={130}
                            height={35}
                            priority
                            className="h-9 w-auto"
                        />
                    </Link>

                    {/* Nav links — hidden when search is open */}
                    {!searchOpen && (
                        <nav
                            className="ml-10 hidden items-center gap-0.5 lg:flex"
                            aria-label="Main navigation"
                            onMouseLeave={() => setHoveredLabel(null)}
                        >
                            {NAV.map((item) => {
                                const isActive = hoveredLabel === item.label || activeDropdown === item.label;

                                if (item.href) {
                                    return (
                                        <Link
                                            key={item.label}
                                            href={item.href}
                                            className={`group relative flex h-[60px] items-center px-4 text-[14px] transition-colors ${isActive ? textActive : textColor}`}
                                            onMouseEnter={() => setHoveredLabel(item.label)}
                                        >
                                            {item.label}
                                            <span
                                                aria-hidden="true"
                                                className={`pointer-events-none absolute bottom-0 left-4 right-4 h-[2px] origin-center ${underlineColor} transition-transform duration-300 ease-out ${
                                                    isActive ? 'scale-x-100' : 'scale-x-0'
                                                }`}
                                            />
                                        </Link>
                                    );
                                }

                                return (
                                    <div
                                        key={item.label}
                                        className="relative"
                                        onMouseEnter={() => setHoveredLabel(item.label)}
                                    >
                                        <button
                                            type="button"
                                            aria-haspopup="true"
                                            aria-expanded={activeDropdown === item.label}
                                            onClick={() => toggleDropdown(item.label)}
                                            className={`flex h-[60px] items-center px-4 text-[14px] transition-colors ${
                                                isActive ? textActive : textColor
                                            }`}
                                        >
                                            {item.label}
                                        </button>
                                        <span
                                            aria-hidden="true"
                                            className={`pointer-events-none absolute bottom-0 left-4 right-4 h-[2px] origin-center ${underlineColor} transition-transform duration-300 ease-out ${
                                                isActive ? 'scale-x-100' : 'scale-x-0'
                                            }`}
                                        />
                                    </div>
                                );
                            })}
                        </nav>
                    )}

                    {/* Spacer when search is open to push search to fill */}
                    {searchOpen && <div className="hidden flex-1 lg:block" />}

                    <div className={`flex items-center gap-4 ${searchOpen ? 'flex-1 lg:ml-8' : ''}`}>
                        <ExpandableSearch searchOpen={searchOpen} setSearchOpen={setSearchOpen} />
                        <Link href="/contact" className="hidden h-12 shrink-0 items-center rounded-full bg-[#2563eb] px-8 text-[15px] font-medium text-white transition-colors hover:bg-[#1d4ed8] lg:inline-flex">
                            Get in touch
                        </Link>
                        <button aria-label="Open menu" onClick={() => setMobileOpen(true)} className={`lg:hidden ${dark ? 'text-white/60' : 'text-black/60'}`}>
                            <Menu className="h-5 w-5" />
                        </button>
                    </div>
                </div>
            </header>

            <div ref={dropdownRef}>
                {activeDropdown && !searchOpen && NAV.find((n) => n.label === activeDropdown && n.columns) && (
                    <MegaDropdown item={NAV.find((n) => n.label === activeDropdown)!} onClose={closeDropdown} />
                )}
            </div>

            {mobileOpen && <MobileMenu onClose={() => setMobileOpen(false)} />}
        </>
    );
}
