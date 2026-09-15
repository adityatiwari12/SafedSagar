import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'
import { UserPersona, UserRole, VerificationStatus } from './authApi'

export interface AdminUserSummary {
  id: string
  email: string
  role: UserRole
  persona: UserPersona | null
  verification_status: VerificationStatus
  created_at: string
}

export interface AdminStats {
  users_by_role: Record<string, number>
  open_cases: number
  closed_cases: number
}

export const adminApi = {
  listUsers(): Promise<AdminUserSummary[]> {
    return apiFetch<AdminUserSummary[]>('/admin/users', {}, getStoredToken())
  },
  stats(): Promise<AdminStats> {
    return apiFetch<AdminStats>('/admin/stats', {}, getStoredToken())
  },
}
