import { apiRequest } from './client';
import type { CurrentUser } from './types';

export function login(email: string, password: string): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/auth/login', { method: 'POST', body: { email, password } });
}

export function logout(): Promise<{ detail: string }> {
  return apiRequest<{ detail: string }>('/auth/logout', { method: 'POST' });
}

export function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/auth/me');
}
