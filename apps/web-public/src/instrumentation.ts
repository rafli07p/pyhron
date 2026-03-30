export async function register() {
  if (process.env.NEXT_PUBLIC_USE_MSW === 'true') {
    if (typeof window === 'undefined' && process.env.NEXT_RUNTIME === 'nodejs') {
      const { server } = await import('@/lib/mock/server');
      server.listen({ onUnhandledRequest: 'bypass' });
    }
  }
}
