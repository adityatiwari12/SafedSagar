import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'

export interface CaseItem {
  id: string
  status: 'open' | 'in_progress' | 'closed'
  // Backend CaseStatus/CaseQueue/CaseRiskLevel have a wider value set than
  // the `status` union above already accounted for (app/db/models.py) -
  // kept as plain strings here so a value this type doesn't enumerate
  // doesn't fail to typecheck, matching how `status` itself is handled.
  queue: string | null
  risk_level: string
  question: string
  answer: string
  reason: string | null
  product_classification: string | null
  // subset of app.graph.state.IP_TYPES (patent/trademark/design/...) - the
  // IP regimes this case's question touched.
  ip_types: string[] | null
  jurisdiction: string | null
  confidence_score: number | null
  confidence_level: string | null
  assigned_facilitator_email: string | null
  user_email: string
  created_at: string
  closed_at: string | null
  resolution_summary: string | null
  // Additive: which Product dossier (if any) this case is linked to -
  // null for a case not tied to a specific product.
  product_id: string | null
  product_name: string | null
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
