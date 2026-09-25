import { useEffect, useState } from 'react'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { adminApi, SourceSummary } from '../api/adminApi'
import { ApiError } from '../api/http'
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from '../ui/primitives'

export default function KnowledgeBasePage() {
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [jurisdictionFilter, setJurisdictionFilter] = useState<'' | 'india' | 'international'>('')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setSources(await adminApi.listKnowledgeBase())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load knowledge base')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const visible = sources.filter((s) => !jurisdictionFilter || s.jurisdiction === jurisdictionFilter)
  const totalChunks = sources.reduce((sum, s) => sum + s.chunk_count, 0)

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        <PageHeader
          title="Knowledge Base"
          description="Every source document in the ingested RAG corpus — what the assistant can actually cite from, with authority, jurisdiction, version and verification date."
        />

        {!loading && !error && sources.length > 0 && (
          <div className="flex flex-wrap gap-3 border border-surface-border bg-white p-3">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">Documents</p>
              <p className="text-lg font-extrabold text-navy">{sources.length}</p>
            </div>
            <div className="border-l border-surface-border pl-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">Indexed chunks</p>
              <p className="text-lg font-extrabold text-navy">{totalChunks}</p>
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {(['', 'india', 'international'] as const).map((j) => (
            <button
              key={j || 'all'}
              type="button"
              onClick={() => setJurisdictionFilter(j)}
              className={`gov-btn-secondary !py-1 text-xs ${jurisdictionFilter === j ? 'border-primary bg-primary/10' : ''}`}
            >
              {j === '' ? 'All' : j === 'india' ? 'India' : 'International'}
            </button>
          ))}
          <button type="button" onClick={() => void load()} className="gov-btn-secondary !py-1 text-xs">
            Refresh
          </button>
        </div>

        {error && (
          <div>
            <ErrorState message={error} />
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {loading && <LoadingState label="Loading knowledge base…" />}

        {!loading && !error && visible.length === 0 && (
          <EmptyState title="No sources in this view" description="Try a different jurisdiction filter." />
        )}

        {!loading && !error && visible.length > 0 && (
          <div className="overflow-x-auto border border-surface-border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-ivory/80 text-[11px] uppercase tracking-wide text-ink-faint">
                <tr>
                  <th className="px-4 py-2">Title</th>
                  <th className="px-4 py-2">Authority</th>
                  <th className="px-4 py-2">Jurisdiction</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Version</th>
                  <th className="px-4 py-2">Last verified</th>
                  <th className="px-4 py-2">Chunks</th>
                  <th className="px-4 py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((s) => (
                  <tr key={s.doc_id} className="border-b border-line/60 align-top">
                    <td className="py-2 pr-4 text-ink">{s.title}</td>
                    <td className="py-2 pr-4 text-ink-muted">{s.authority}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status="open" label={s.jurisdiction} />
                    </td>
                    <td className="py-2 pr-4 text-ink-muted">{s.doc_type.replace(/_/g, ' ')}</td>
                    <td className="py-2 pr-4 text-ink-muted">{s.version ?? '—'}</td>
                    <td className="py-2 pr-4 text-ink-muted">{s.last_verified_date ?? '—'}</td>
                    <td className="py-2 pr-4 text-ink-muted">{s.chunk_count}</td>
                    <td className="py-2 pr-4">
                      {s.source_url ? (
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-forest hover:underline"
                        >
                          Official source
                        </a>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
