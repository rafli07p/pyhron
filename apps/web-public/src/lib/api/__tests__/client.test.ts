import { ApiError, api } from '@/lib/api/client';

vi.mock('next-auth/react', () => ({
  getSession: vi.fn(),
}));

import { getSession } from 'next-auth/react';

const mockGetSession = vi.mocked(getSession);

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  vi.clearAllMocks();
  mockGetSession.mockResolvedValue(null);
});

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

describe('ApiError', () => {
  it('has correct status and detail', () => {
    const err = new ApiError(404, 'Not found');
    expect(err.status).toBe(404);
    expect(err.detail).toBe('Not found');
    expect(err.name).toBe('ApiError');
    expect(err.message).toBe('Not found');
  });
});

describe('apiFetch (via api.get)', () => {
  it('throws ApiError with correct status on 400 response', async () => {
    mockFetch.mockResolvedValue(jsonResponse(400, { detail: 'Bad request' }));
    await expect(api.get('/test')).rejects.toThrow(ApiError);
    await expect(api.get('/test')).rejects.toMatchObject({ status: 400 });
  });

  it('throws ApiError with correct status on 401 response', async () => {
    mockFetch.mockResolvedValue(jsonResponse(401, { detail: 'Unauthorized' }));
    await expect(api.get('/test')).rejects.toThrow(ApiError);
    await expect(api.get('/test')).rejects.toMatchObject({ status: 401 });
  });

  it('throws ApiError with correct status on 403 response', async () => {
    mockFetch.mockResolvedValue(jsonResponse(403, { detail: 'Forbidden' }));
    await expect(api.get('/test')).rejects.toThrow(ApiError);
    await expect(api.get('/test')).rejects.toMatchObject({ status: 403 });
  });

  it('throws ApiError on 404 with detail from response body', async () => {
    mockFetch.mockResolvedValue(jsonResponse(404, { detail: 'Resource not found' }));
    await expect(api.get('/missing')).rejects.toMatchObject({
      status: 404,
      detail: 'Resource not found',
    });
  });

  it('attaches Authorization header when session has accessToken', async () => {
    mockGetSession.mockResolvedValue({ accessToken: 'tok_abc123' } as any);
    mockFetch.mockResolvedValue(jsonResponse(200, { ok: true }));

    await api.get('/secure');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/secure',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer tok_abc123',
        }),
      }),
    );
  });

  it('omits Authorization header when no session', async () => {
    mockGetSession.mockResolvedValue(null);
    mockFetch.mockResolvedValue(jsonResponse(200, { data: [] }));

    await api.get('/public');

    const headers = mockFetch.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('returns parsed JSON on successful response', async () => {
    const payload = { id: 1, name: 'BBCA' };
    mockFetch.mockResolvedValue(jsonResponse(200, payload));

    const result = await api.get('/instruments/BBCA');
    expect(result).toEqual(payload);
  });
});
