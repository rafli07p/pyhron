'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search, User, Menu, X } from 'lucide-react';
import { Footer } from '@/components/landing/footer';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const isLanding = pathname === '/';

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 10);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? 'bg-white/95 shadow-sm backdrop-blur-sm'
          : isLanding
            ? 'bg-transparent'
            : 'bg-white'
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-12">
        {/* Logo */}
        <Link href="/" className="text-lg font-light tracking-[0.2em] text-[#0A1628]">
          PYHRON
        </Link>

        {/* Right icons */}
        <div className="flex items-center gap-5">
          <button aria-label="Search" className="text-[#0A1628]/60 transition-colors hover:text-[#0A1628]">
            <Search className="h-[18px] w-[18px]" strokeWidth={1.5} />
          </button>
          <Link href="/login" aria-label="Sign in" className="text-[#0A1628]/60 transition-colors hover:text-[#0A1628]">
            <User className="h-[18px] w-[18px]" strokeWidth={1.5} />
          </Link>
          <button
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen(!menuOpen)}
            className="text-[#0A1628]/60 transition-colors hover:text-[#0A1628]"
          >
            {menuOpen ? (
              <X className="h-[18px] w-[18px]" strokeWidth={1.5} />
            ) : (
              <Menu className="h-[18px] w-[18px]" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>

      {/* Slide-down menu */}
      {menuOpen && (
        <div className="border-t border-[#E5E7EB] bg-white">
          <nav className="mx-auto max-w-7xl px-6 py-8 lg:px-12">
            <div className="grid grid-cols-2 gap-x-12 gap-y-4 md:grid-cols-4">
              {[
                { label: 'Research', href: '/research' },
                { label: 'Pricing', href: '/pricing' },
                { label: 'Methodology', href: '/methodology' },
                { label: 'About', href: '/about' },
                { label: 'Contact', href: '/contact' },
                { label: 'Sign In', href: '/login' },
                { label: 'Create Account', href: '/register' },
              ].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="text-sm text-[#6B7280] transition-colors hover:text-[#0A1628]"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="light flex min-h-screen flex-col bg-white text-[#1A1A2E]">
      <Navbar />
      <main id="main-content" className="flex-1">{children}</main>
      <Footer />
      <div className="border-t border-white/5 bg-[#0A1628] px-6 py-4">
        <FinancialDisclaimer className="mx-auto max-w-6xl text-white/30" />
      </div>
    </div>
  );
}
