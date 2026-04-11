'use client';

import Link from 'next/link';
import Image from 'next/image';
import { PublicNavbar } from '@/components/layout/PublicNavbar';

const leftLinks = [
  { label: 'Terms of use', href: '/legal/terms' },
  { label: 'Privacy notice', href: '/legal/privacy' },
  { label: 'Legal', href: '/legal/disclaimer' },
  { label: 'Modern Slavery Statement', href: '/legal/disclaimer' },
  { label: 'Manage cookies', href: '/legal/privacy' },
];

const rightLinks = [
  { label: 'Contact us', href: '/contact' },
  { label: 'Office locations', href: '/contact' },
  { label: 'Index regulation', href: '/methodology' },
  { label: 'Resources for issuers', href: '/methodology' },
  { label: 'Use of ISO standards', href: '/methodology' },
];

function PublicFooter() {
  return (
    <footer className="bg-black text-white">
      <div className="mx-auto max-w-[1400px] px-6 py-16 lg:px-12 lg:py-20">
        {/* Logo */}
        <Link href="/" className="inline-flex items-center">
          <Image
            src="/logos/logo.svg"
            alt="Pyhron"
            width={160}
            height={42}
            className="h-10 w-auto invert"
          />
        </Link>

        {/* Link columns */}
        <div className="mt-14 grid grid-cols-1 gap-y-6 md:grid-cols-2 md:gap-x-16">
          <ul className="space-y-6">
            {leftLinks.map((link) => (
              <li key={link.label}>
                <Link
                  href={link.href}
                  className="text-[16px] font-normal text-white transition-opacity hover:opacity-75"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          <ul className="space-y-6">
            {rightLinks.map((link) => (
              <li key={link.label}>
                <Link
                  href={link.href}
                  className="text-[16px] font-normal text-white transition-opacity hover:opacity-75"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Bottom bar */}
        <div className="mt-16 flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <p className="text-[13px] text-white/50">
            &copy; 2026 Pyhron Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-5 text-white/85">
            <a
              href="https://x.com/pyhron"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="X (Twitter)"
              className="transition-opacity hover:opacity-75"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M18.244 2H21l-6.52 7.451L22.5 22h-6.906l-4.75-6.214L5.25 22H2.5l6.974-7.966L1.5 2h7.08l4.289 5.66L18.244 2Zm-1.212 18h1.83L7.062 3.9H5.11l11.922 16.1Z" />
              </svg>
            </a>
            <a
              href="https://linkedin.com/company/pyhron"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="LinkedIn"
              className="transition-opacity hover:opacity-75"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M20.45 20.45h-3.555v-5.57c0-1.328-.025-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.94v5.667H9.352V9h3.414v1.561h.047c.476-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.285ZM5.337 7.433a2.062 2.062 0 1 1 0-4.124 2.062 2.062 0 0 1 0 4.124ZM7.118 20.45H3.553V9h3.565v11.45ZM22.227 0H1.77C.792 0 0 .774 0 1.729v20.542C0 23.226.792 24 1.77 24h20.454C23.206 24 24 23.226 24 22.271V1.729C24 .774 23.206 0 22.227 0Z" />
              </svg>
            </a>
            <a
              href="https://youtube.com/@pyhron"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="YouTube"
              className="transition-opacity hover:opacity-75"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814ZM9.545 15.568V8.432L15.818 12l-6.273 3.568Z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="light flex min-h-screen flex-col bg-white text-[#1a1a1a]">
      <PublicNavbar />
      <main id="main-content" className="flex-1 pt-[88px]">{children}</main>
      <PublicFooter />
    </div>
  );
}
