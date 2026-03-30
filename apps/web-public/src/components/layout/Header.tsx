'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, Search, ChevronDown } from 'lucide-react';
import { ThemeToggle } from '@/components/shared/ThemeToggle';
import { mainNav, type NavLink, type MegaMenuSection } from '@/lib/constants/navigation';

function MegaMenuDropdown({
  sections,
  onClose,
}: {
  sections: MegaMenuSection[];
  onClose: () => void;
}) {
  return (
    <div className="absolute left-0 top-full w-full bg-bg-primary/95 backdrop-blur-md border-b border-border shadow-lg z-50 max-h-[70vh] overflow-y-auto">
      <div className="mx-auto max-w-content px-6 py-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {sections.map((section) => (
            <div key={section.title}>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">
                {section.title}
              </h3>
              <ul className="space-y-2">
                {section.items.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onClose}
                      className="group block rounded-md px-2 py-1.5 -mx-2 hover:bg-bg-tertiary transition-colors"
                    >
                      <span className="text-sm font-medium text-text-primary group-hover:text-accent-500 transition-colors">
                        {item.label}
                      </span>
                      {item.description && (
                        <p className="mt-0.5 text-xs text-text-muted line-clamp-1">
                          {item.description}
                        </p>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MobileMenu({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [expandedMenu, setExpandedMenu] = useState<string | null>(null);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-80 max-w-[85vw] bg-bg-primary border-l border-border overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <span className="font-display text-lg">Menu</span>
          <button onClick={onClose} aria-label="Close menu">
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="p-4">
          {mainNav.map((link) => (
            <div key={link.label} className="border-b border-border last:border-0">
              {link.megaMenu ? (
                <>
                  <button
                    onClick={() =>
                      setExpandedMenu(expandedMenu === link.label ? null : link.label)
                    }
                    className="flex w-full items-center justify-between py-3 text-sm font-medium"
                  >
                    {link.label}
                    <ChevronDown
                      className={`h-4 w-4 transition-transform ${expandedMenu === link.label ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {expandedMenu === link.label && (
                    <div className="pb-3 pl-3">
                      {link.megaMenu.map((section) => (
                        <div key={section.title} className="mb-4">
                          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
                            {section.title}
                          </p>
                          {section.items.map((item) => (
                            <Link
                              key={item.href}
                              href={item.href}
                              onClick={onClose}
                              className="block py-1.5 text-sm text-text-secondary hover:text-accent-500"
                            >
                              {item.label}
                            </Link>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <Link
                  href={link.href || '/'}
                  onClick={onClose}
                  className="block py-3 text-sm font-medium"
                >
                  {link.label}
                </Link>
              )}
            </div>
          ))}
          <div className="mt-4 space-y-2">
            <Link
              href="/login"
              onClick={onClose}
              className="block w-full rounded-md border border-border px-4 py-2 text-center text-sm font-medium hover:bg-bg-tertiary transition-colors"
            >
              Log in
            </Link>
            <Link
              href="/register"
              onClick={onClose}
              className="block w-full rounded-md bg-accent-500 px-4 py-2 text-center text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </nav>
      </div>
    </div>
  );
}

export function Header() {
  const pathname = usePathname();
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const headerRef = useRef<HTMLElement>(null);

  const handleMouseEnter = useCallback((label: string) => {
    clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setActiveMenu(label), 250);
  }, []);

  const handleMouseLeave = useCallback(() => {
    clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setActiveMenu(null), 150);
  }, []);

  useEffect(() => {
    setActiveMenu(null);
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setActiveMenu(null);
        setMobileOpen(false);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (headerRef.current && !headerRef.current.contains(e.target as Node)) {
        setActiveMenu(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header
      ref={headerRef}
      className="sticky top-0 z-40 border-b border-border bg-bg-primary/95 backdrop-blur-md"
    >
      <a href="#main-content" className="skip-to-content">
        Skip to content
      </a>
      <div className="mx-auto flex h-16 max-w-content items-center justify-between px-6">
        <Link href="/" className="font-display text-xl tracking-wide text-text-primary">
          PYHRON
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" role="navigation">
          {mainNav.map((link) => (
            <div
              key={link.label}
              className="relative"
              onMouseEnter={() => link.megaMenu && handleMouseEnter(link.label)}
              onMouseLeave={() => link.megaMenu && handleMouseLeave()}
            >
              {link.megaMenu ? (
                <button
                  className={`flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:text-accent-500 ${
                    activeMenu === link.label ? 'text-accent-500' : 'text-text-secondary'
                  }`}
                  aria-expanded={activeMenu === link.label}
                  onClick={() =>
                    setActiveMenu(activeMenu === link.label ? null : link.label)
                  }
                >
                  {link.label}
                  <ChevronDown
                    className={`h-3.5 w-3.5 transition-transform ${activeMenu === link.label ? 'rotate-180' : ''}`}
                  />
                </button>
              ) : (
                <Link
                  href={link.href || '/'}
                  className="rounded-md px-3 py-2 text-sm font-medium text-text-secondary transition-colors hover:text-accent-500"
                >
                  {link.label}
                </Link>
              )}
            </div>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
              document.dispatchEvent(event);
            }}
            className="hidden items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-text-muted hover:bg-bg-tertiary transition-colors sm:flex"
            aria-label="Search"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Search...</span>
            <kbd className="hidden rounded border border-border bg-bg-tertiary px-1.5 py-0.5 text-xs md:inline">
              ⌘K
            </kbd>
          </button>
          <ThemeToggle />
          <Link
            href="/login"
            className="hidden rounded-md px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors lg:block"
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="hidden rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors lg:block"
          >
            Get Started
          </Link>
          <button
            onClick={() => setMobileOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-md lg:hidden"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Desktop MegaMenu */}
      {mainNav.map(
        (link) =>
          link.megaMenu &&
          activeMenu === link.label && (
            <div
              key={link.label}
              onMouseEnter={() => handleMouseEnter(link.label)}
              onMouseLeave={handleMouseLeave}
            >
              <MegaMenuDropdown
                sections={link.megaMenu}
                onClose={() => setActiveMenu(null)}
              />
            </div>
          ),
      )}

      {/* Mobile Menu */}
      <MobileMenu isOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
    </header>
  );
}
