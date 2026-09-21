import { useEffect, useState } from 'react'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import {
  ConfidenceBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusBadge,
} from '../ui/primitives'
import { RiskBadge } from '../cases/caseBadges'
import { casesApi, CaseItem } from '../api/casesApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

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

  const band =
    item.confidence_level === 'high' ||
    item.confidence_level === 'medium' ||
    item.confidence_level === 'low'
      ? item.confidence_level
      : 'insufficient'

  return (
    <article className="space-y-4 border border-surface-border bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={item.status} />
          <RiskBadge risk={item.risk_level} />
          {item.product_name && <StatusBadge status="medium" label={item.product_name} />}
        </div>
        <span className="text-xs text-ink-faint">{new Date(item.created_at).toLocaleString()}</span>
      </div>

      <section>
        <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
          User question
        </h3>
        <p className="mt-1 text-sm text-ink">{item.question}</p>
      </section>

      {item.answer && (
        <section>
          <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
            AI assessment
          </h3>
          <p className="mt-1 whitespace-pre-wrap text-sm text-ink-muted">{item.answer}</p>
        </section>
      )}

      <div className="grid gap-4 border-t border-surface-border pt-3 sm:grid-cols-2">
        <section>
          <h3 className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
            Classification · Jurisdiction
          </h3>
          <div className="flex flex-wrap gap-2">
            <StatusBadge
              status="medium"
              label={(item.product_classification ?? 'unclassified').replace(/_/g, ' ')}
            />
            <StatusBadge status="open" label={item.jurisdiction ?? 'not set'} />
          </div>
          <p className="mt-2 text-xs text-ink-muted">User: {item.user_email}</p>
        </section>
        <section>
          <h3 className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
            Confidence
          </h3>
          <ConfidenceBadge
            band={band}
            confidence={item.confidence_score ?? undefined}
            reason={item.reason ?? undefined}
          />
        </section>
      </div>

      {item.reason && (
        <p className="border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          <span className="font-semibold">Escalation reason:</span> {item.reason}
        </p>
      )}

      {item.assigned_facilitator_email && (
        <p className="text-xs text-ink-muted">
          Assigned to <span className="font-semibold text-ink">{item.assigned_facilitator_email}</span>
        </p>
      )}

      {item.status === 'closed' ? (
        <p className="border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900">
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

      {error && <ErrorState message={error} />}
    </article>
  )
}

export default function CasesPage() {
  const { user } = useAuth()
  const [cases, setCases] = useState<CaseItem[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isExpert = user?.role === 'regulatory_expert'
  const title = isExpert ? 'Expert validation queue' : 'Facilitator case queue'
  const description = isExpert
    ? 'Validate AI assessments against evidence, correct conclusions, and request missing information.'
    : 'Triage escalations — claim open items, close with a resolution, or escalate further when needed.'

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
    <AppWorkspaceShell>
      <PageHeader title={title} description={description} />
      <div className="space-y-5">
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

        {error && <ErrorState message={error} />}
        {loading && <LoadingState label="Loading cases…" />}

        {!loading && cases.length === 0 && (
          <EmptyState
            title="No cases in this view"
            description="Ask a low-confidence or out-of-scope question as a User to see an escalation appear here."
          />
        )}

        <div className="space-y-4">
          {cases.map((c) => (
            <CaseCard key={c.id} item={c} onChanged={() => void load()} />
          ))}
        </div>
      </div>
    </AppWorkspaceShell>
  )
}
