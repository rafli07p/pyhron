export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: string;
  tenant_id: string;
  created_at: string;
}

export type UserRole = 'ADMIN' | 'TRADER' | 'ANALYST' | 'VIEWER';
