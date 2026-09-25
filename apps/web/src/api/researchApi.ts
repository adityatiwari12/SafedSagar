import { apiFetch } from './http'
import { getStoredToken } from '../auth/AuthContext'

export interface PriorArtResult {
  doc_id: string
  title: string
  authority: string
  jurisdiction: 'india' | 'international'
  doc_type: string
  section_or_article: string | null
  source_url: string
  snippet: string
}

export const researchApi = {
  searchPriorArt(q: string, jurisdiction?: 'india' | 'international' | null): Promise<PriorArtResult[]> {
    const params = new URLSearchParams({ q })
    if (jurisdiction) params.set('jurisdiction', jurisdiction)
    return apiFetch<PriorArtResult[]>(`/research/prior-art?${params.toString()}`, {}, getStoredToken())
  },
}
