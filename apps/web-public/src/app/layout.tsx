import type { Metadata } from 'next';
import { Providers } from '@/components/shared/Providers';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { CommandPalette } from '@/components/shared/CommandPalette';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Pyhron - Quantitative Analytics and Trading for IDX',
    template: '%s | Pyhron',
  },
  description:
    'Factor models, algorithmic trading, and portfolio analytics for the Indonesia Stock Exchange.',
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    title: 'Pyhron',
    description: 'Quantitative analytics and trading for IDX',
    siteName: 'Pyhron',
    locale: 'en_US',
    type: 'website',
  },
  twitter: { card: 'summary_large_image' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen font-body antialiased">
        <Providers>
          <Header />
          <main id="main-content">{children}</main>
          <Footer />
          <CommandPalette />
        </Providers>
      </body>
    </html>
  );
}
