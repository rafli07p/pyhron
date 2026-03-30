import Link from 'next/link';
import { footerNav } from '@/lib/constants/navigation';

export function Footer() {
  return (
    <footer className="border-t border-border bg-bg-secondary">
      <div className="mx-auto max-w-content px-6 py-16">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-muted">
              Solutions
            </h3>
            <ul className="space-y-2">
              {footerNav.solutions.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-sm text-text-secondary hover:text-accent-500 transition-colors"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-muted">
              Research
            </h3>
            <ul className="space-y-2">
              {footerNav.research.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-sm text-text-secondary hover:text-accent-500 transition-colors"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-muted">
              Company
            </h3>
            <ul className="space-y-2">
              {footerNav.company.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-sm text-text-secondary hover:text-accent-500 transition-colors"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-muted">
              Legal
            </h3>
            <ul className="space-y-2">
              {footerNav.legal.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-sm text-text-secondary hover:text-accent-500 transition-colors"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border pt-8 md:flex-row">
          <div className="flex items-center gap-2">
            <span className="font-display text-lg">PYHRON</span>
            <span className="text-sm text-text-muted">
              Quantitative analytics for IDX
            </span>
          </div>
          <p className="text-xs text-text-muted">
            &copy; {new Date().getFullYear()} Pyhron. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
