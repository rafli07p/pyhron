import 'next-auth';

declare module 'next-auth' {
  interface Session {
    accessToken: string;
    error?: string;
    user: {
      id: string;
      email: string;
      name: string;
      role: string;
      tier: 'explorer' | 'strategist' | 'operator';
    };
  }

  interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    tier: 'explorer' | 'strategist' | 'operator';
    accessToken: string;
    refreshToken: string;
    accessTokenExpires: number;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id: string;
    role: string;
    tier: 'explorer' | 'strategist' | 'operator';
    accessToken: string;
    refreshToken: string;
    accessTokenExpires: number;
    error?: string;
  }
}
