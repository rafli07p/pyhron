export interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'analyst' | 'admin';
  plan: 'free' | 'pro' | 'enterprise';
  createdAt: string;
  lastLoginAt: string;
}
