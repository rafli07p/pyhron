import { getSession, signOut } from 'next-auth/react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL!;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public detail: string,
    public field?: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

export class AuthError extends ApiError {
  constructor(detail = 'Authentication required') {
    super(401, 'AUTH_REQUIRED', detail);
  }
}

export class RateLimitError extends ApiError {
  constructor(public retryAfter: number) {
    super(429, 'RATE_LIMITED', `Rate limited. Retry after ${retryAfter}s`);
  }
}

export class NetworkError extends Error {
  constructor() {
    super('Network error — check your connection');
    this.name = 'NetworkError';
  }
}

class ApiClient {
  private inflightRequests = new Map<string, Promise<unknown>>();

  async request<T>(
    endpoint: string,
    options: RequestInit & {
      dedupe?: string;
      timeout?: number;
      skipAuth?: boolean;
    } = {},
  ): Promise<T> {
    const { dedupe, timeout = 30_000, skipAuth = false, ...fetchOptions } = options;

    if (dedupe && this.inflightRequests.has(dedupe)) {
      return this.inflightRequests.get(dedupe) as Promise<T>;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort('Timeout'), timeout);

    const requestPromise = (async () => {
      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          'X-Request-ID': crypto.randomUUID(),
          ...((fetchOptions.headers as Record<string, string>) || {}),
        };

        if (!skipAuth) {
          const session = await getSession();
          if (!session?.accessToken) {
            if (session?.error === 'RefreshTokenExpired') {
              await signOut({ callbackUrl: '/login?reason=session_expired' });
            }
            throw new AuthError();
          }
          headers['Authorization'] = `Bearer ${session.accessToken}`;
        }

        const res = await fetch(`${API_BASE}${endpoint}`, {
          ...fetchOptions,
          headers,
          signal: controller.signal,
        });

        if (res.status === 401) {
          await signOut({ callbackUrl: '/login?reason=session_expired' });
          throw new AuthError();
        }

        if (res.status === 429) {
          const retryAfter = parseInt(res.headers.get('Retry-After') || '60', 10);
          throw new RateLimitError(retryAfter);
        }

        if (!res.ok) {
          const body = await res.json().catch(() => ({ code: 'UNKNOWN', detail: 'Request failed' }));
          throw new ApiError(res.status, body.code, body.detail, body.field);
        }

        if (res.status === 204) return undefined as T;
        return (await res.json()) as T;
      } catch (err) {
        if (err instanceof TypeError && err.message.includes('fetch')) {
          throw new NetworkError();
        }
        throw err;
      } finally {
        clearTimeout(timeoutId);
        if (dedupe) this.inflightRequests.delete(dedupe);
      }
    })();

    if (dedupe) this.inflightRequests.set(dedupe, requestPromise);
    return requestPromise;
  }

  get<T>(endpoint: string, opts?: Parameters<typeof this.request>[1]) {
    return this.request<T>(endpoint, { ...opts, method: 'GET' });
  }
  post<T>(endpoint: string, body: unknown, opts?: Parameters<typeof this.request>[1]) {
    return this.request<T>(endpoint, { ...opts, method: 'POST', body: JSON.stringify(body) });
  }
  put<T>(endpoint: string, body: unknown, opts?: Parameters<typeof this.request>[1]) {
    return this.request<T>(endpoint, { ...opts, method: 'PUT', body: JSON.stringify(body) });
  }
  delete<T>(endpoint: string, opts?: Parameters<typeof this.request>[1]) {
    return this.request<T>(endpoint, { ...opts, method: 'DELETE' });
  }
}

export const api = new ApiClient();
