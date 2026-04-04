'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Search, User, Menu, X } from 'lucide-react';

export function PublicNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 80);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? 'border-b border-[var(--border-default)] bg-[rgba(9,9,11,0.85)] backdrop-blur-xl backdrop-saturate-150'
          : 'bg-transparent'
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-12">
        <Link
          href="/"
          className="text-sm font-light tracking-[0.25em] text-[var(--text-primary)]"
        >
          PYHRON
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {[
            { href: '/research', label: 'Research' },
            { href: '/pricing', label: 'Pricing' },
            { href: '/methodology', label: 'Methodology' },
            { href: '/about', label: 'About' },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-xs font-medium text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <button
            aria-label="Search"
            className="text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
          >
            <Search className="h-4 w-4" strokeWidth={1.5} />
          </button>
          <Link
            href="/login"
            aria-label="Sign in"
            className="text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
          >
            <User className="h-4 w-4" strokeWidth={1.5} />
          </Link>
          <button
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen(!menuOpen)}
            className="text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)] md:hidden"
          >
            {menuOpen ? (
              <X className="h-4 w-4" strokeWidth={1.5} />
            ) : (
              <Menu className="h-4 w-4" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="border-t border-[var(--border-default)] bg-[var(--surface-0)] px-6 py-6 md:hidden">
          {[
            { href: '/research', label: 'Research' },
            { href: '/pricing', label: 'Pricing' },
            { href: '/methodology', label: 'Methodology' },
            { href: '/about', label: 'About' },
            { href: '/login', label: 'Sign In' },
            { href: '/register', label: 'Create Account' },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className="block py-2 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
