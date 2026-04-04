import type { Metadata } from 'next';
import { AppProviders } from '@/components/providers/AppProviders';
import { SkipToContent } from '@/components/common/SkipToContent';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3001'),
  title: {
    default: 'Pyhron — Quantitative Research for Indonesia\'s Capital Markets',
    template: '%s — Pyhron',
  },
  description:
    'Institutional-grade quantitative research and algorithmic trading platform for the Indonesia Stock Exchange (IDX).',
  keywords: [
    'quantitative trading', 'algorithmic trading', 'IDX', 'Indonesia Stock Exchange',
    'quant research', 'backtesting', 'risk management', 'IHSG',
  ],
  openGraph: {
    type: 'website',
    locale: 'id_ID',
    alternateLocale: 'en_US',
    siteName: 'Pyhron',
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" suppressHydrationWarning>
      <body className="min-h-screen font-sans antialiased">
        <SkipToContent />
        <AppProviders>
          {children}
          {/* Screen reader announcer — status updates after animations */}
          <div id="sr-announcer" aria-live="polite" aria-atomic="true" className="sr-only" role="status" />
        </AppProviders>
      </body>
    </html>
  );
}
