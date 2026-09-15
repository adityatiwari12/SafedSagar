import { useEffect, useState } from 'react'
import { AppShell } from '../layout/AppShell'
import { casesApi, CaseItem } from '../api/casesApi'
import { ApiError } from '../api/http'

const STATUS_STYLES: Record<CaseItem['status'], string> = {
  open: 'bg-red-50 text-red-900 border-red-700',
  in_progress: 'bg-amber-100 text-amber-950 border-amber-700',
  closed: 'bg-green-100 text-green-900 border-green-700',
}

function CaseCard({ item, onChanged }: { item: CaseItem; onChanged: () => void }) {
  const [resolution, setResolution] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function claim() {
    setBusy(true)
    setError(null)
    try {
      await casesApi.claim(item.id)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to claim case')
    } finally {
      setBusy(false)
    }
  }

  async function close() {
    if (!resolution.trim()) {
      setError('Add a resolution summary before closing.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await casesApi.close(item.id, resolution.trim())
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to close case')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="gov-panel space-y-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`inline-flex items-center rounded-sm border px-2.5 py-1 text-xs font-bold uppercase tracking-wide ${STATUS_STYLES[item.status]}`}
        >
          {item.status.replace('_', ' ')}
        </span>
        <span className="text-xs text-ink-faint">
          {new Date(item.created_at).toLocaleString()}
        </span>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Question</p>
        <p className="mt-1 text-sm text-ink">{item.question}</p>
      </div>

      {item.answer && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">AI answer</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-ink-muted">{item.answer}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs text-ink-muted sm:grid-cols-4">
        <div>
          <span className="font-semibold text-ink">User:</span> {item.user_email}
        </div>
        <div>
          <span className="font-semibold text-ink">Classification:</span>{' '}
          {item.product_classification ?? 'n/a'}
        </div>
        <div>
          <span className="font-semibold text-ink">Jurisdiction:</span> {item.jurisdiction ?? 'n/a'}
        </div>
        <div>
          <span className="font-semibold text-ink">Confidence:</span>{' '}
          {item.confidence_level ?? 'n/a'}
          {item.confidence_score != null ? ` (${Math.round(item.confidence_score * 100)}%)` : ''}
        </div>
      </div>

      {item.reason && (
        <p className="rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          <span className="font-semibold">Why escalated:</span> {item.reason}
        </p>
      )}

      {item.assigned_facilitator_email && (
        <p className="text-xs text-ink-muted">
          Assigned to <span className="font-semibold text-ink">{item.assigned_facilitator_email}</span>
        </p>
      )}

      {item.status === 'closed' ? (
        <p className="rounded-sm border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900">
          <span className="font-semibold">Resolved:</span> {item.resolution_summary}
        </p>
      ) : (
        <div className="space-y-2 border-t border-line pt-3">
          {item.status === 'open' && (
            <button type="button" className="gov-btn-secondary" onClick={claim} disabled={busy}>
              Claim this case
            </button>
          )}
          {item.status === 'in_progress' && (
            <div className="space-y-2">
              <label className="gov-label" htmlFor={`resolution-${item.id}`}>
                Resolution summary
              </label>
              <textarea
                id={`resolution-${item.id}`}
                className="gov-input"
                rows={2}
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                placeholder="What did you tell the user? Why is this resolved?"
              />
              <button type="button" className="gov-btn-primary" onClick={close} disabled={busy}>
                {busy ? 'Closing…' : 'Close case'}
              </button>
            </div>
          )}
        </div>
      )}

      {error && (
        <p className="rounded-sm bg-red-50 px-3 py-2 text-xs text-red-800" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export default function CasesPage() {
  const [cases, setCases] = useState<CaseItem[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await casesApi.list(statusFilter || undefined)
      setCases(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load cases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter])

  return (
    <AppShell>
      <div className="space-y-5">
        <header>
          <h1 className="text-2xl font-bold text-navy">Escalated case queue</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Questions the AI flagged for human review — low confidence, no validated citations, or
            an unclear product classification.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-2">
          {['', 'open', 'in_progress', 'closed'].map((s) => (
            <button
              key={s || 'all'}
              type="button"
              onClick={() => setStatusFilter(s)}
              className={`gov-btn-secondary !py-1 text-xs ${statusFilter === s ? 'border-primary bg-primary/10' : ''}`}
            >
              {s === '' ? 'All' : s.replace('_', ' ')}
            </button>
          ))}
          <button type="button" onClick={() => void load()} className="gov-btn-secondary !py-1 text-xs">
            Refresh
          </button>
        </div>

        {error && (
          <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
            {error}
          </p>
        )}

        {loading && <p className="text-sm text-ink-muted">Loading cases…</p>}

        {!loading && cases.length === 0 && (
          <div className="gov-panel border-dashed p-6 text-center text-sm text-ink-muted">
            No cases in this view. Ask a low-confidence or out-of-scope question as a User to see
            one appear here.
          </div>
        )}

        <div className="space-y-4">
          {cases.map((c) => (
            <CaseCard key={c.id} item={c} onChanged={() => void load()} />
          ))}
        </div>
      </div>
    </AppShell>
  )
}
