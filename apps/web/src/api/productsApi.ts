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
}

export function humanizeClassification(value: string | null | undefined): string {
  if (!value) return 'Unclassified'
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
