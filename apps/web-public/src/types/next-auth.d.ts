import 'next-auth';

declare module 'next-auth' {
  interface Session {
    accessToken: string;
    error?: string;
    user: { id: string; email: string; name: string; role: string };
  }
  interface User {
    id: string;
    role: string;
    accessToken: string;
    refreshToken: string;
    expiresAt: number;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    role?: string;
    userId?: string;
    error?: string;
  }
}
