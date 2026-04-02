import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const authHandlers = [
  http.post(`${API_BASE}/v1/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    if (body.email === 'demo@pyhron.com' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'mock-access-token-' + Date.now(),
        refresh_token: 'mock-refresh-token-' + Date.now(),
        token_type: 'bearer',
        expires_in: 900,
      });
    }
    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
  }),

  http.post(`${API_BASE}/v1/auth/register`, async () => {
    return HttpResponse.json({
      id: crypto.randomUUID(),
      email: 'new@pyhron.com',
      full_name: 'New User',
      is_active: true,
      role: 'VIEWER',
      tenant_id: 'default',
      created_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  http.post(`${API_BASE}/v1/auth/refresh`, () => {
    return HttpResponse.json({
      access_token: 'mock-refreshed-token-' + Date.now(),
      refresh_token: 'mock-refresh-token-' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
    });
  }),

  http.get(`${API_BASE}/v1/auth/me`, () => {
    return HttpResponse.json({
      id: '550e8400-e29b-41d4-a716-446655440000',
      email: 'demo@pyhron.com',
      full_name: 'Demo User',
      is_active: true,
      role: 'TRADER',
      tenant_id: 'default',
      created_at: '2024-01-01T00:00:00Z',
    });
  }),
];
