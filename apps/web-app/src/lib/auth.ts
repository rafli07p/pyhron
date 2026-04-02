import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

const BACKEND_URL = process.env.BACKEND_URL!;

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    CredentialsProvider({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const res = await fetch(`${BACKEND_URL}/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
        });

        if (!res.ok) {
          const error = await res.json().catch(() => ({ detail: 'Login failed' }));
          throw new Error(error.detail || 'Invalid credentials');
        }

        const data = await res.json();

        // Fetch user profile
        const profileRes = await fetch(`${BACKEND_URL}/v1/auth/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        const profile = profileRes.ok
          ? await profileRes.json()
          : { id: 'unknown', email: credentials.email, full_name: '', role: 'VIEWER' };

        return {
          id: profile.id,
          email: profile.email,
          name: profile.full_name || profile.email.split('@')[0],
          role: profile.role,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          accessTokenExpires: Date.now() + data.expires_in * 1000,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) return { ...token, ...user };

      const expiresAt = token.accessTokenExpires as number;
      if (Date.now() < expiresAt - 2 * 60 * 1000) return token;

      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      session.user.id = token.id as string;
      session.user.role = token.role as string;
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
