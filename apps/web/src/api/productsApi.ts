import { apiFetch, apiFetchBlob, API_BASE, ApiError } from './http'
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

export const ABS_ORIGINS = ['india', 'outside_india', 'unknown'] as const
export type AbsOrigin = (typeof ABS_ORIGINS)[number]

export const ABS_SOURCINGS = ['wild_collected', 'cultivated', 'both', 'unknown'] as const
export type AbsSourcing = (typeof ABS_SOURCINGS)[number]

export const ABS_PURPOSES = ['commercial', 'research_only', 'unknown'] as const
export type AbsPurpose = (typeof ABS_PURPOSES)[number]

export const ABS_ENTITY_CATEGORIES = [
  'indian_individual',
  'indian_company',
  'foreign_entity',
  'unknown',
] as const
export type AbsEntityCategory = (typeof ABS_ENTITY_CATEGORIES)[number]

export type AbsAssessmentStatus = 'not_started' | 'in_progress' | 'complete'

export interface AbsEvidence {
  doc_id: string
  section_or_article?: string | null
  title: string
  authority?: string | null
  source_url?: string | null
}

export interface AbsAssessment {
  id: string | null
  product_id: string
  is_biological_resource: boolean | null
  resource_description: string | null
  origin: AbsOrigin | null
  sourcing: AbsSourcing | null
  involves_traditional_knowledge: boolean | null
  purpose: AbsPurpose | null
  user_entity_category: AbsEntityCategory | null
  preliminary_framework: string | null
  applicable_provisions: AbsEvidence[] | null
  next_steps: string[] | null
  status: AbsAssessmentStatus
  updated_by_user_id: string | null
  created_at: string | null
  updated_at: string | null
}

/** The wizard's answerable fields — the shape sent to PUT. This is always
 * a full replace server-side (see AbsAssessmentUpdate on the backend), so
 * callers must always send the complete current answer set, never a
 * partial patch of just the step being edited. */
export type AbsAssessmentInput = {
  is_biological_resource?: boolean | null
  resource_description?: string | null
  origin?: AbsOrigin | null
  sourcing?: AbsSourcing | null
  involves_traditional_knowledge?: boolean | null
  purpose?: AbsPurpose | null
  user_entity_category?: AbsEntityCategory | null
}

export const DOC_KINDS = ['label', 'certificate', 'formulation_sheet', 'correspondence', 'other'] as const
export type DocKind = (typeof DOC_KINDS)[number]

export interface DocumentMeta {
  id: string
  owner_user_id: string
  organization_id: string | null
  product_id: string | null
  case_id: string | null
  filename: string
  content_type: string
  size_bytes: number
  doc_kind: DocKind
  status: 'active' | 'deleted'
  uploaded_by_user_id: string
  created_at: string
}

export const DOCUMENT_ALLOWED_CONTENT_TYPES = ['application/pdf', 'image/png', 'image/jpeg'] as const
export const DOCUMENT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024

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
  getAbsAssessment(productId: string): Promise<AbsAssessment> {
    return apiFetch<AbsAssessment>(`/products/${productId}/abs`, {}, getStoredToken())
  },
  /** PUT is a full replace server-side — `input` must always be the
   * complete current answer set, not just the field(s) being edited. */
  saveAbsAssessment(
    productId: string,
    input: AbsAssessmentInput,
    withEvidence = false,
  ): Promise<AbsAssessment> {
    return apiFetch<AbsAssessment>(
      `/products/${productId}/abs?with_evidence=${withEvidence ? 'true' : 'false'}`,
      { method: 'PUT', body: JSON.stringify(input) },
      getStoredToken(),
    )
  },
  listDocuments(productId: string): Promise<DocumentMeta[]> {
    return apiFetch<DocumentMeta[]>(
      `/documents?product_id=${encodeURIComponent(productId)}`,
      {},
      getStoredToken(),
    )
  },
  /** Every document the caller can see (own uploads + accessible
   * products' + accessible cases') - the same GET /documents endpoint as
   * listDocuments, just without the product_id filter. Backend already
   * scopes this correctly (app/documents/router.py's list_documents). */
  listAllDocuments(): Promise<DocumentMeta[]> {
    return apiFetch<DocumentMeta[]>('/documents', {}, getStoredToken())
  },
  /** Multipart upload — bypasses apiFetch (JSON-only: it would force a
   * `Content-Type: application/json` header onto a FormData body, breaking
   * the multipart boundary) in favour of a raw XMLHttpRequest so real
   * upload progress can be reported via `onProgress`. */
  uploadDocument(
    input: { file: File; docKind: DocKind; productId: string },
    onProgress?: (pct: number) => void,
  ): Promise<DocumentMeta> {
    return new Promise((resolve, reject) => {
      const form = new FormData()
      form.append('file', input.file)
      form.append('doc_kind', input.docKind)
      form.append('product_id', input.productId)

      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${API_BASE}/documents`)
      const token = getStoredToken()
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

      xhr.upload.onprogress = (e) => {
        if (onProgress && e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }

      xhr.onload = () => {
        let body: unknown = null
        try {
          body = JSON.parse(xhr.responseText)
        } catch {
          // no/invalid JSON body
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as DocumentMeta)
        } else {
          const detail =
            body && typeof body === 'object' && 'detail' in body
              ? (body as { detail: unknown }).detail
              : xhr.statusText
          reject(new ApiError(xhr.status, typeof detail === 'string' ? detail : JSON.stringify(detail)))
        }
      }
      xhr.onerror = () => reject(new ApiError(0, 'Network error during upload'))
      xhr.send(form)
    })
  },
  downloadDocument(documentId: string): Promise<{ blob: Blob; filename: string | null }> {
    return apiFetchBlob(`/documents/${documentId}/download`, getStoredToken())
  },
  removeDocument(documentId: string): Promise<void> {
    return apiFetch<void>(`/documents/${documentId}`, { method: 'DELETE' }, getStoredToken())
  },
  downloadReport(productId: string): Promise<{ blob: Blob; filename: string | null }> {
    return apiFetchBlob(`/products/${productId}/report`, getStoredToken())
  },
}

export function humanizeClassification(value: string | null | undefined): string {
  if (!value) return 'Unclassified'
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function humanizeArea(area: string): string {
  return area.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function humanizeDocKind(kind: string): string {
  return kind.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/** e.g. 2400000 -> "2.3 MB". Matches units a non-technical user expects
 * (1024-based, one decimal place above the first unit). */
export function humanFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unitIndex]}`
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
