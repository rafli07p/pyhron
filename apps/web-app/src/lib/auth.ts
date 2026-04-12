import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const IS_DEV = process.env.NEXT_PUBLIC_ENVIRONMENT === 'development';

// Dev-mode demo accounts (used when backend is unreachable)
const DEV_USERS: Record<string, { password: string; id: string; name: string; role: string; tier: string }> = {
  'demo@pyhron.com': { password: 'password123', id: '550e8400-e29b-41d4-a716-446655440000', name: 'Demo User', role: 'TRADER', tier: 'strategist' },
  'admin@pyhron.com': { password: 'admin123', id: '550e8400-e29b-41d4-a716-446655440001', name: 'Admin User', role: 'ADMIN', tier: 'operator' },
};

async function tryBackendLogin(email: string, password: string) {
  const res = await fetch(`${BACKEND_URL}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Invalid credentials');
  }

  const data = await res.json();

  const profileRes = await fetch(`${BACKEND_URL}/v1/auth/me`, {
    headers: { Authorization: `Bearer ${data.access_token}` },
  });
  const profile = profileRes.ok
    ? await profileRes.json()
    : { id: 'unknown', email, full_name: '', role: 'VIEWER' };

  return {
    id: profile.id,
    email: profile.email,
    name: profile.full_name || email.split('@')[0],
    role: profile.role,
    tier: profile.tier ?? 'explorer',
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    accessTokenExpires: Date.now() + data.expires_in * 1000,
  };
}

function devLogin(email: string, password: string) {
  const user = DEV_USERS[email];
  if (!user || user.password !== password) return null;

  return {
    id: user.id,
    email,
    name: user.name,
    role: user.role,
    tier: user.tier,
    accessToken: `dev-token-${Date.now()}`,
    refreshToken: `dev-refresh-${Date.now()}`,
    accessTokenExpires: Date.now() + 24 * 60 * 60 * 1000, // 24h for dev
  };
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    CredentialsProvider({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const email = credentials.email as string;
        const password = credentials.password as string;

        // Try real backend first
        try {
          return await tryBackendLogin(email, password);
        } catch (backendError) {
          // In dev mode, fall back to mock users if backend is unreachable
          if (IS_DEV) {
            const devUser = devLogin(email, password);
            if (devUser) return devUser;
          }
          throw backendError;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) return { ...token, ...user };

      const expiresAt = token.accessTokenExpires as number;
      if (Date.now() < expiresAt - 2 * 60 * 1000) return token;

      // Skip refresh for dev tokens
      if ((token.accessToken as string)?.startsWith('dev-token-')) {
        return { ...token, accessTokenExpires: Date.now() + 24 * 60 * 60 * 1000 };
      }

      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      session.user.id = token.id as string;
      session.user.role = token.role as string;
      session.user.tier = (token.tier as 'explorer' | 'strategist' | 'operator') ?? 'explorer';
      session.accessToken = token.accessToken as string;
      session.error = token.error as string | undefined;
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: { strategy: 'jwt', maxAge: 7 * 24 * 60 * 60 },
});

async function refreshAccessToken(token: Record<string, unknown>) {
  try {
    const res = await fetch(`${BACKEND_URL}/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    });
    if (!res.ok) throw new Error(`Refresh failed: ${res.status}`);
    const data = await res.json();
    return {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token ?? token.refreshToken,
      accessTokenExpires: Date.now() + data.expires_in * 1000,
      error: undefined,
    };
  } catch {
    return { ...token, error: 'RefreshTokenExpired' };
  }
}
