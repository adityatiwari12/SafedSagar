import { apiFetch } from './http'

export interface UserProfile {
  id: string
  email: string
  role: 'user' | 'facilitator' | 'admin'
  jurisdiction_preference: string | null
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export const authApi = {
  register(email: string, password: string): Promise<UserProfile> {
    return apiFetch<UserProfile>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  login(email: string, password: string): Promise<AuthTokens> {
    const body = new URLSearchParams({ username: email, password })
    return apiFetch<AuthTokens>('/auth/login', { method: 'POST', body })
  },

  me(token: string): Promise<UserProfile> {
    return apiFetch<UserProfile>('/auth/me', {}, token)
  },
}
