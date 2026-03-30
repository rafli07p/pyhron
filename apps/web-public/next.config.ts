import type { NextConfig } from 'next';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

const config: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',

  async rewrites() {
    return [
      { source: '/api/v1/:path*', destination: `${FASTAPI_URL}/v1/:path*` },
      { source: '/openapi.json', destination: `${FASTAPI_URL}/openapi.json` },
    ];
  },

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              `connect-src 'self' ${FASTAPI_URL} wss://*`,
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "frame-ancestors 'none'",
            ].join('; '),
          },
        ],
      },
    ];
  },
};

export default config;
