export { auth as middleware } from '@/lib/auth';

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/studio/:path*',
    '/markets/:path*',
    '/research/:path*',
    '/strategies/:path*',
    '/portfolio/:path*',
    '/execution/:path*',
    '/data/:path*',
    '/ml/:path*',
    '/alerts/:path*',
    '/settings/:path*',
    '/admin/:path*',
  ],
};
