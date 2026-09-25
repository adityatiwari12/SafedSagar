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

export interface SourceSummary {
  doc_id: string
  title: string
  authority: string
  jurisdiction: 'india' | 'international'
  doc_type: string
  version: string | null
  effective_date: string | null
  last_verified_date: string | null
  source_url: string | null
  chunk_count: number
}

export interface AuditLogEntryOut {
  id: string
  actor_user_id: string | null
  actor_email: string | null
  action: string
  detail: Record<string, unknown> | null
  created_at: string
}

export const adminApi = {
  listUsers(): Promise<AdminUserSummary[]> {
    return apiFetch<AdminUserSummary[]>('/admin/users', {}, getStoredToken())
  },
  stats(): Promise<AdminStats> {
    return apiFetch<AdminStats>('/admin/stats', {}, getStoredToken())
  },
  listKnowledgeBase(): Promise<SourceSummary[]> {
    return apiFetch<SourceSummary[]>('/admin/knowledge-base', {}, getStoredToken())
  },
  listAuditLogs(limit = 200): Promise<AuditLogEntryOut[]> {
    return apiFetch<AuditLogEntryOut[]>(`/admin/audit-logs?limit=${limit}`, {}, getStoredToken())
  },
}
