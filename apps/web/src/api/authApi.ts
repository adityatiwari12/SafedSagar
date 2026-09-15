import { apiFetch } from './http'

export type UserRole = 'user' | 'facilitator' | 'regulatory_expert' | 'admin'
export type UserPersona = 'entrepreneur' | 'practitioner_researcher' | 'cultivator'
export type VerificationStatus = 'approved' | 'pending' | 'rejected'

// Roles a signup form may offer - never 'admin' (seeded server-side only;
// the backend also rejects it with 422 if sent, this is belt-and-braces).
export type SelfRegisterableRole = Extract<UserRole, 'user' | 'facilitator' | 'regulatory_expert'>

export interface UserProfile {
  id: string
  email: string
  role: UserRole
  persona: UserPersona | null
  verification_status: VerificationStatus
  jurisdiction_preference: string | null
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export interface RegisterOptions {
  role?: SelfRegisterableRole
  persona?: UserPersona
}

export const authApi = {
  register(email: string, password: string, options: RegisterOptions = {}): Promise<UserProfile> {
    return apiFetch<UserProfile>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, ...options }),
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
