import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'
import { CaseItem } from './casesApi'

export const PRODUCT_CLASSIFICATIONS = [
  'classical_or_generic_medicine',
  'patent_or_proprietary_medicine',
  'new_or_non_classical_drug',
  'phytopharmaceutical',
  'ayurveda_aahara_or_nutraceutical',
  'cosmetic',
  'unclear',
  'out_of_scope',
] as const

export type ProductClassification = (typeof PRODUCT_CLASSIFICATIONS)[number]

export interface Ingredient {
  name: string
  quantity?: string | null
}

export interface Product {
  id: string
  owner_user_id: string
  organization_id?: string | null
  name: string
  description?: string | null
  product_classification?: ProductClassification | null
  jurisdiction?: 'india' | 'international' | null
  intended_use?: string | null
  claims?: string | null
  manufacturing_info?: string | null
  target_market?: string | null
  development_stage?: string | null
  ingredients?: Ingredient[] | null
  biological_resources?: string[] | null
  ip_status?: Record<string, unknown> | null
  regulatory_status?: Record<string, unknown> | null
  abs_tk_status?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type ProductCreateInput = {
  name: string
  description?: string | null
  product_classification?: ProductClassification | null
  jurisdiction?: 'india' | 'international' | null
  intended_use?: string | null
  development_stage?: string | null
}

export type ProductPatchInput = Partial<Omit<Product, 'id' | 'owner_user_id' | 'created_at' | 'updated_at'>>

export const COMPLIANCE_AREAS = [
  'classification',
  'manufacturing',
  'ingredients',
  'safety_evidence',
  'labelling',
  'claims',
  'advertising',
  'licensing',
  'food_requirements',
  'cosmetic_requirements',
] as const

export type ComplianceArea = (typeof COMPLIANCE_AREAS)[number]

export const COMPLIANCE_STATUSES = [
  'unknown',
  'action_required',
  'under_review',
  'complete',
  'not_applicable',
] as const

export type ComplianceStatus = (typeof COMPLIANCE_STATUSES)[number]

export interface ComplianceEvidence {
  doc_id: string
  section_or_article?: string | null
  title: string
  authority: string
  source_url?: string | null
}

export interface ComplianceItem {
  id: string
  product_id: string
  area: ComplianceArea
  status: ComplianceStatus
  applicability_reason: string
  notes?: string | null
  evidence?: ComplianceEvidence[] | null
  updated_by_user_id?: string | null
  created_at: string
  updated_at: string
}

export type ComplianceSummary = Record<ComplianceStatus, number> & { total: number }

export interface ComplianceChecklist {
  items: ComplianceItem[]
  summary: ComplianceSummary
}

export type ComplianceItemPatch = {
  status?: ComplianceStatus
  notes?: string | null
}

export const productsApi = {
  list(): Promise<Product[]> {
    return apiFetch<Product[]>('/products', {}, getStoredToken())
  },
  get(id: string): Promise<Product> {
    return apiFetch<Product>(`/products/${id}`, {}, getStoredToken())
  },
  create(input: ProductCreateInput): Promise<Product> {
    return apiFetch<Product>(
      '/products',
      { method: 'POST', body: JSON.stringify(input) },
      getStoredToken(),
    )
  },
  update(id: string, patch: ProductPatchInput): Promise<Product> {
    return apiFetch<Product>(
      `/products/${id}`,
      { method: 'PATCH', body: JSON.stringify(patch) },
      getStoredToken(),
    )
  },
  remove(id: string): Promise<void> {
    return apiFetch<void>(`/products/${id}`, { method: 'DELETE' }, getStoredToken())
  },
  getCases(id: string): Promise<CaseItem[]> {
    return apiFetch<CaseItem[]>(`/products/${id}/cases`, {}, getStoredToken())
  },
  getCompliance(id: string): Promise<ComplianceChecklist> {
    return apiFetch<ComplianceChecklist>(`/products/${id}/compliance`, {}, getStoredToken())
  },
  generateCompliance(id: string, withEvidence = false): Promise<ComplianceChecklist> {
    return apiFetch<ComplianceChecklist>(
      `/products/${id}/compliance?with_evidence=${withEvidence ? 'true' : 'false'}`,
      { method: 'POST' },
      getStoredToken(),
    )
  },
  updateComplianceItem(
    productId: string,
    itemId: string,
    patch: ComplianceItemPatch,
  ): Promise<ComplianceItem> {
    return apiFetch<ComplianceItem>(
      `/products/${productId}/compliance/${itemId}`,
      { method: 'PATCH', body: JSON.stringify(patch) },
      getStoredToken(),
    )
  },
}

export function humanizeClassification(value: string | null | undefined): string {
  if (!value) return 'Unclassified'
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function humanizeArea(area: string): string {
  return area.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Recomputes the per-status summary from a checklist's items — used after
 * an optimistic PATCH so the summary strip never drifts from the rows
 * actually on screen, instead of trusting a server summary that may be
 * stale relative to a local edit still in flight. */
export function summarizeCompliance(items: ComplianceItem[]): ComplianceSummary {
  const summary = {
    unknown: 0,
    action_required: 0,
    under_review: 0,
    complete: 0,
    not_applicable: 0,
    total: items.length,
  } as ComplianceSummary
  for (const item of items) {
    summary[item.status] += 1
  }
  return summary
}
