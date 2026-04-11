import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { AppProviders } from '@/components/providers/AppProviders';
import { SkipToContent } from '@/components/common/SkipToContent';
import './globals.css';

// Inter is the font MSCI.com uses (see the @font-face for `__Inter_f367f3`
// shipped from their Next.js bundle). We load the same weights plus the
// italic variant so headings and body copy match MSCI's typographic system.
const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3001'),
  title: {
    default: 'Pyhron',
    template: '%s — Pyhron',
  },
  description: 'Bringing Clarity to Investment Decisions',
  keywords: [
    'quantitative trading', 'algorithmic trading', 'IDX', 'Indonesia Stock Exchange',
    'quant research', 'backtesting', 'risk management', 'IHSG',
  ],
  icons: {
    icon: '/logos/favicon.ico',
    shortcut: '/logos/favicon-32x32.png',
    apple: '/logos/apple-touch-icon.png',
  },
  openGraph: {
    images: [{ url: '/logos/og-image.png', width: 1200, height: 630 }],
    type: 'website',
    locale: 'id_ID',
    alternateLocale: 'en_US',
    siteName: 'Pyhron',
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
      <html lang="id" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen font-sans antialiased">
      <SkipToContent />
      <AppProviders>
        {children}
        <div id="sr-announcer" aria-live="polite" aria-atomic="true" className="sr-only" role="status" />
      </AppProviders>
      </body>
      </html>
  );
}