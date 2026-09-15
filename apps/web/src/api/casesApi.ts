import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'

export interface CaseItem {
  id: string
  status: 'open' | 'in_progress' | 'closed'
  question: string
  answer: string
  reason: string | null
  product_classification: string | null
  jurisdiction: string | null
  confidence_score: number | null
  confidence_level: string | null
  assigned_facilitator_email: string | null
  user_email: string
  created_at: string
  closed_at: string | null
  resolution_summary: string | null
}

export const casesApi = {
  list(statusFilter?: string): Promise<CaseItem[]> {
    const qs = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : ''
    return apiFetch<CaseItem[]>(`/cases${qs}`, {}, getStoredToken())
  },
  claim(id: string): Promise<CaseItem> {
    return apiFetch<CaseItem>(`/cases/${id}/claim`, { method: 'POST' }, getStoredToken())
  },
  close(id: string, resolutionSummary: string): Promise<CaseItem> {
    return apiFetch<CaseItem>(
      `/cases/${id}/close`,
      { method: 'POST', body: JSON.stringify({ resolution_summary: resolutionSummary }) },
      getStoredToken(),
    )
  },
}
