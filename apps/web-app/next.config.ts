import type { NextConfig } from 'next';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM equivalent of CommonJS `__dirname` — used below to pin Turbopack's
// module-resolution root to this directory (apps/web-app), so a stray
// `package-lock.json` anywhere up the tree can't confuse workspace
// inference and make imports like `gsap` resolve from the wrong
// node_modules.
const webAppDir = path.dirname(fileURLToPath(import.meta.url));

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const securityHeaders = [
  { key: 'X-DNS-Prefetch-Control', value: 'on' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-XSS-Protection', value: '1; mode=block' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
];

const config: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',

  turbopack: {
    // Force Turbopack's workspace root to this package instead of letting
    // it auto-detect from the nearest lockfile. Without this, a stray
    // `package-lock.json` at the monorepo root makes Turbopack try to
    // resolve dependencies from the repo root's (non-existent) node_modules
    // and fail with "Module not found" on legit deps like `gsap`.
    root: webAppDir,
  },

  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24,
  },

  async rewrites() {
    return [
      { source: '/api/v1/:path*', destination: `${BACKEND_URL}/v1/:path*` },
    ];
  },

  async headers() {
    return [
      {
        source: '/fonts/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
    ];
  },

};

export default config;
