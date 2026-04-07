import Link from 'next/link';

const linkGroups = [
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

export function Footer() {
  return (
    <footer className="bg-[#0A1628] py-16">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-5">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <p className="text-lg font-normal tracking-[0.15em] text-white">PYHRON</p>
            <p className="mt-2 text-xs leading-relaxed text-white/40">
              Quantitative research and algorithmic trading infrastructure for Indonesian capital markets.
            </p>
          </div>
          {linkGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-[10px] font-medium uppercase tracking-[0.15em] text-white/40">
                {group.title}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {group.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-white/60 transition-colors hover:text-white"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 md:flex-row">
          <p className="text-xs text-white/30">
            &copy; 2025 Pyhron. All rights reserved. Not registered with OJK.
          </p>
          <div className="flex gap-6">
            <Link href="/legal/privacy" className="text-xs text-white/30 hover:text-white/60">
              Privacy
            </Link>
            <Link href="/legal/terms" className="text-xs text-white/30 hover:text-white/60">
              Terms
            </Link>
            <Link href="/legal/disclaimer" className="text-xs text-white/30 hover:text-white/60">
              Disclaimer
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
