export async function register() {
  if (process.env.NEXT_PUBLIC_USE_MSW === 'true') {
    if (typeof window === 'undefined') {
      const { server } = await import('@/lib/mock/server');
      server.listen({ onUnhandledRequest: 'bypass' });
    }
  }
}
