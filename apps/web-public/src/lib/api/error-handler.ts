import { signOut } from 'next-auth/react';
import { toast } from 'sonner';
import { ApiError } from './client';

export function handleApiError(error: unknown) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        toast.error('Session expired. Signing out.');
        signOut({ callbackUrl: '/login' });
        break;
      case 403:
        toast.error('Permission denied.');
        break;
      case 429:
        toast.error('Rate limited. Wait a moment.');
        break;
      case 404:
        toast.error('Not found.');
        break;
      default:
        toast.error(error.detail || 'Request failed.');
    }
  } else {
    toast.error('Network error.');
  }
}
