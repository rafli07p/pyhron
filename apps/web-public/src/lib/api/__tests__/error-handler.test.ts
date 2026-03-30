import { ApiError } from '@/lib/api/client';
import { handleApiError } from '@/lib/api/error-handler';

vi.mock('next-auth/react', () => ({ signOut: vi.fn() }));
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

import { signOut } from 'next-auth/react';
import { toast } from 'sonner';

const mockSignOut = vi.mocked(signOut);
const mockToastError = vi.mocked(toast.error);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('handleApiError', () => {
  it('calls signOut with callbackUrl /login on 401 ApiError', () => {
    handleApiError(new ApiError(401, 'Unauthorized'));
    expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: '/login' });
  });

  it('shows "Permission denied." toast on 403 ApiError', () => {
    handleApiError(new ApiError(403, 'Forbidden'));
    expect(mockToastError).toHaveBeenCalledWith('Permission denied.');
  });

  it('shows "Rate limited. Wait a moment." toast on 429 ApiError', () => {
    handleApiError(new ApiError(429, 'Too many requests'));
    expect(mockToastError).toHaveBeenCalledWith('Rate limited. Wait a moment.');
  });

  it('shows "Not found." toast on 404 ApiError', () => {
    handleApiError(new ApiError(404, 'Not found'));
    expect(mockToastError).toHaveBeenCalledWith('Not found.');
  });

  it('shows "Network error." toast for unknown error (not ApiError)', () => {
    handleApiError(new Error('fetch failed'));
    expect(mockToastError).toHaveBeenCalledWith('Network error.');
  });

  it('shows the detail message for ApiError with other status', () => {
    handleApiError(new ApiError(500, 'Internal server error'));
    expect(mockToastError).toHaveBeenCalledWith('Internal server error');
  });
});
