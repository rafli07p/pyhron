export { auth as middleware } from '@/lib/auth';

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/markets/:path*',
    '/research/:path*',
    '/strategies/:path*',
    '/portfolio/:path*',
    '/execution/:path*',
    '/data/:path*',
    '/ml/:path*',
    '/settings/:path*',
    '/admin/:path*',
  ],
};
