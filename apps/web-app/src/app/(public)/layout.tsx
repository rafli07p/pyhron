'use client';

import Link from 'next/link';
import { PublicNavbar } from '@/components/layout/PublicNavbar';
import { SmoothScrollProvider } from '@/components/providers/SmoothScrollProvider';

function PublicFooter() {
  const groups = [
    {
      title: 'Platform',
      links: [
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Markets', href: '/markets' },
        { label: 'Studio', href: '/studio' },
        { label: 'Portfolio', href: '/portfolio' },
      ],
    },
    {
      title: 'Research',
      links: [
        { label: 'Insights', href: '/research/articles' },
        { label: 'Signals', href: '/research/signals' },
        { label: 'Methodology', href: '/methodology' },
      ],
    },
    {
      title: 'Company',
      links: [
        { label: 'About', href: '/about' },
        { label: 'Pricing', href: '/pricing' },
        { label: 'Contact', href: '/contact' },
      ],
    },
    {
      title: 'Legal',
      links: [
        { label: 'Terms', href: '/legal/terms' },
        { label: 'Privacy', href: '/legal/privacy' },
        { label: 'Disclaimer', href: '/legal/disclaimer' },
      ],
    },
  ];

  return (
    <footer className="border-t border-[var(--border-default)] bg-[var(--surface-1)]">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-5">
          <div className="col-span-2 md:col-span-1">
            <p className="text-sm font-light tracking-[0.2em] text-[var(--text-primary)]">PYHRON</p>
            <p className="mt-2 text-xs leading-relaxed text-[var(--text-tertiary)]">
              Quantitative research and algorithmic trading infrastructure for Indonesian capital markets.
            </p>
          </div>
          {groups.map((group) => (
            <div key={group.title}>
              <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                {group.title}
              </h3>
              <ul className="mt-3 space-y-2">
                {group.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-8 border-t border-[var(--border-default)] pt-8">
          <p className="text-xs text-[var(--text-tertiary)]">
            &copy; 2025 Pyhron. All rights reserved. Not registered with OJK.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <SmoothScrollProvider>
      <div className="flex min-h-screen flex-col">
        <PublicNavbar />
        <main id="main-content" className="flex-1">{children}</main>
        <PublicFooter />
      </div>
    </SmoothScrollProvider>
  );
}
