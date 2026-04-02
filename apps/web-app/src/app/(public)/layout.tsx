import Link from 'next/link';
import { Logo } from '@/components/common/Logo';
import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 flex h-14 items-center border-b border-[var(--border-default)] bg-[var(--surface-0)]/80 px-6 backdrop-blur-sm">
        <Link href="/">
          <Logo />
        </Link>
        <nav className="ml-auto flex items-center gap-4">
          <Link href="/research" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            Research
          </Link>
          <Link href="/pricing" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            Pricing
          </Link>
          <Link
            href="/login"
            className="rounded-md bg-[var(--accent-500)] px-4 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-600)]"
          >
            Sign In
          </Link>
        </nav>
      </header>
      <main id="main-content" className="flex-1">{children}</main>
      <footer className="border-t border-[var(--border-default)] bg-[var(--surface-1)]">
        <div className="mx-auto max-w-7xl px-6 py-12">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Platform</h3>
              <ul className="mt-3 space-y-2">
                <li><Link href="/dashboard" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Dashboard</Link></li>
                <li><Link href="/markets" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Markets</Link></li>
                <li><Link href="/strategies" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Strategies</Link></li>
                <li><Link href="/portfolio" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Portfolio</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Research</h3>
              <ul className="mt-3 space-y-2">
                <li><Link href="/research" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Insights</Link></li>
                <li><Link href="/indexes" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Indexes</Link></li>
                <li><Link href="/methodology" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Methodology</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Company</h3>
              <ul className="mt-3 space-y-2">
                <li><Link href="/about" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">About</Link></li>
                <li><Link href="/pricing" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Pricing</Link></li>
                <li><Link href="/contact" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Contact</Link></li>
                <li><Link href="/changelog" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Changelog</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Legal</h3>
              <ul className="mt-3 space-y-2">
                <li><Link href="/legal/terms" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Terms</Link></li>
                <li><Link href="/legal/privacy" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Privacy</Link></li>
                <li><Link href="/legal/disclaimer" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">Disclaimer</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 border-t border-[var(--border-default)] pt-8">
            <p className="text-xs text-[var(--text-tertiary)]">© 2025 Pyhron. Not registered with OJK.</p>
            <FinancialDisclaimer className="mt-4" />
          </div>
        </div>
      </footer>
    </div>
  );
}
