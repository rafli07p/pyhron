import type { NextAuthConfig } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

export const authConfig: NextAuthConfig = {
  providers: [
    Credentials({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        const res = await fetch(`${FASTAPI_URL}/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: credentials?.email,
            password: credentials?.password,
          }),
        });

        if (!res.ok) {
          const error = await res.json().catch(() => ({ detail: 'Login failed' }));
          throw new Error(error.detail || 'Invalid credentials');
        }

        const tokens = await res.json();

        const profileRes = await fetch(`${FASTAPI_URL}/v1/auth/me`, {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        });
        if (!profileRes.ok) throw new Error('Failed to fetch profile');
        const profile = await profileRes.json();

        return {
          id: profile.id,
          email: profile.email,
          name: profile.full_name,
          role: profile.role,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          expiresAt: Math.floor(Date.now() / 1000) + tokens.expires_in,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.expiresAt = user.expiresAt;
        token.role = user.role;
        token.userId = user.id;
      }

      if (Date.now() / 1000 < (token.expiresAt as number)) {
        return token;
      }

      try {
        const res = await fetch(`${FASTAPI_URL}/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: token.refreshToken }),
        });
        if (!res.ok) throw new Error('Refresh failed');
        const refreshed = await res.json();
        return {
          ...token,
          accessToken: refreshed.access_token,
          refreshToken: refreshed.refresh_token,
          expiresAt: Math.floor(Date.now() / 1000) + refreshed.expires_in,
        };
      } catch {
        return { ...token, error: 'RefreshTokenError' };
      }
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.user.id = token.userId as string;
      session.user.role = token.role as string;
      session.error = token.error as string | undefined;
      return session;
    },
  },
  pages: { signIn: '/login', error: '/login' },
  session: { strategy: 'jwt' },
};
