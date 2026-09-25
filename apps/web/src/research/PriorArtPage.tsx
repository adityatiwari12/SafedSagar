import { FormEvent, useState } from 'react'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { ApiError } from '../api/http'
import { PriorArtResult, researchApi } from '../api/researchApi'
import { EmptyState, ErrorState, EvidenceList, LoadingState, PageHeader } from '../ui/primitives'

function toEvidenceItems(results: PriorArtResult[]) {
  return results.map((r) => ({
    title: r.title,
    authority: r.authority,
    provision: r.section_or_article ?? undefined,
    jurisdiction: r.jurisdiction === 'india' ? 'India' : 'International',
    sourceUrl: r.source_url || undefined,
    docId: r.doc_id,
    why: r.snippet,
  }))
}

export default function PriorArtPage() {
  const [query, setQuery] = useState('')
  const [jurisdiction, setJurisdiction] = useState<'india' | 'international' | ''>('')
  const [results, setResults] = useState<PriorArtResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function runSearch(e: FormEvent) {
    e.preventDefault()
    const trimmed = query.trim()
    if (trimmed.length < 3) {
      setError('Enter at least 3 characters to search.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      setResults(await researchApi.searchPriorArt(trimmed, jurisdiction || null))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        <PageHeader
          title="Prior Art"
          description="Search the ingested legal/case-law corpus for related statutes, rules, treaties and judgments. This searches this corpus only — not a live global patent or publication database."
        />

        <form onSubmit={runSearch} className="flex flex-wrap items-end gap-3 border border-surface-border bg-white p-4">
          <div className="min-w-[16rem] flex-1">
            <label className="gov-label" htmlFor="prior-art-query">
              Search terms
            </label>
            <input
              id="prior-art-query"
              className="gov-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. ashwagandha extract patentability, GI infringement scope"
            />
          </div>
          <div>
            <label className="gov-label" htmlFor="prior-art-jurisdiction">
              Jurisdiction
            </label>
            <select
              id="prior-art-jurisdiction"
              className="gov-input"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value as 'india' | 'international' | '')}
            >
              <option value="">All</option>
              <option value="india">India</option>
              <option value="international">International</option>
            </select>
          </div>
          <button type="submit" className="gov-btn-primary !py-2" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>

        {error && <ErrorState message={error} />}
        {loading && <LoadingState label="Searching the corpus…" />}

        {!loading && results !== null && results.length === 0 && (
          <EmptyState
            title="No matches in this corpus"
            description="Try broader terms, or check the Sources page for what's currently ingested. This doesn't mean no prior art exists — only that this corpus doesn't cover it."
          />
        )}

        {!loading && results !== null && results.length > 0 && (
          <div>
            <p className="mb-3 text-xs text-ink-faint">
              {results.length} result{results.length === 1 ? '' : 's'} — always verify against the
              official source before relying on any of these.
            </p>
            <EvidenceList items={toEvidenceItems(results)} />
          </div>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
