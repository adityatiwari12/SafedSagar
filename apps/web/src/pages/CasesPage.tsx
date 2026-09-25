import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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

function CaseCard({
  item,
  onChanged,
  readOnly,
}: {
  item: CaseItem
  onChanged: () => void
  /** A plain 'user' viewing their own submitted cases has neither
   * CASE_ASSIGN nor CASE_CLOSE - claim/close would just 403. Show their
   * status as information, not as actions that will fail. */
  readOnly: boolean
}) {
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
      ) : readOnly ? (
        <p className="border-t border-line pt-3 text-xs text-ink-faint">
          {item.status === 'open'
            ? 'Awaiting a facilitator to pick this up.'
            : 'A facilitator/expert is reviewing this.'}
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

const RISK_WEIGHT: Record<string, number> = { high: 0, medium: 1, low: 2 }
const CONFIDENCE_WEIGHT: Record<string, number> = { low: 0, medium: 1, high: 2, insufficient: -1 }

/** "What needs attention" ordering: highest risk first, then lowest
 * confidence, then oldest first within a tie - so the case most likely to
 * need a human's judgment call is always at the top, not just whatever
 * order the API happened to return. */
function byPriority(a: CaseItem, b: CaseItem): number {
  const riskDiff = (RISK_WEIGHT[a.risk_level] ?? 1) - (RISK_WEIGHT[b.risk_level] ?? 1)
  if (riskDiff !== 0) return riskDiff
  const confDiff =
    (CONFIDENCE_WEIGHT[a.confidence_level ?? 'insufficient'] ?? -1) -
    (CONFIDENCE_WEIGHT[b.confidence_level ?? 'insufficient'] ?? -1)
  if (confDiff !== 0) return confDiff
  return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
}

function AttentionSummary({ cases }: { cases: CaseItem[] }) {
  const open = cases.filter((c) => c.status !== 'closed').length
  const lowConfidence = cases.filter(
    (c) => c.status !== 'closed' && c.confidence_level === 'low',
  ).length
  const highRisk = cases.filter((c) => c.status !== 'closed' && c.risk_level === 'high').length
  const unassigned = cases.filter(
    (c) => c.status === 'open' && !c.assigned_facilitator_email,
  ).length

  if (cases.length === 0) return null

  return (
    <div className="flex flex-wrap gap-3 border border-surface-border bg-white p-3">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">Awaiting you</p>
        <p className="text-lg font-extrabold text-navy">{open}</p>
      </div>
      <div className="border-l border-surface-border pl-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">Low confidence</p>
        <p className="text-lg font-extrabold text-navy">{lowConfidence}</p>
      </div>
      <div className="border-l border-surface-border pl-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">High risk</p>
        <p className="text-lg font-extrabold text-navy">{highRisk}</p>
      </div>
      <div className="border-l border-surface-border pl-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">Unclaimed</p>
        <p className="text-lg font-extrabold text-navy">{unassigned}</p>
      </div>
    </div>
  )
}

export default function CasesPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  // "My Cases" (facilitator, ?scope=mine) and "Compliance Reviews" (expert,
  // ?view=compliance) used to link here and render the identical
  // unfiltered queue - both query params were silently ignored. Both now
  // mean the same real thing: cases already claimed/assigned to me,
  // rather than the full open queue including unclaimed items.
  const mineOnly = searchParams.get('scope') === 'mine' || searchParams.get('view') === 'compliance'
  const [cases, setCases] = useState<CaseItem[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [lowConfidenceOnly, setLowConfidenceOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isExpert = user?.role === 'regulatory_expert'
  const isPlainUser = user?.role === 'user'
  const title = isPlainUser
    ? 'My cases'
    : mineOnly
      ? isExpert
        ? 'Compliance reviews'
        : 'My cases'
      : isExpert
        ? 'Expert validation queue'
        : 'Facilitator case queue'
  const description = isPlainUser
    ? 'Questions you asked that were escalated for human review, and their status.'
    : mineOnly
      ? 'Cases assigned to you specifically, not the full open queue.'
      : isExpert
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

  const visible = [...cases]
    .filter((c) => isPlainUser || !mineOnly || c.assigned_facilitator_email === user?.email)
    .filter((c) => !lowConfidenceOnly || c.confidence_level === 'low')
    .sort(byPriority)

  return (
    <AppWorkspaceShell>
      <PageHeader title={title} description={description} />
      <div className="space-y-5">
        {!isPlainUser && <AttentionSummary cases={cases} />}

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
          <button
            type="button"
            onClick={() => setLowConfidenceOnly((v) => !v)}
            className={`gov-btn-secondary !py-1 text-xs ${lowConfidenceOnly ? 'border-primary bg-primary/10' : ''}`}
          >
            Low confidence only
          </button>
          <button type="button" onClick={() => void load()} className="gov-btn-secondary !py-1 text-xs">
            Refresh
          </button>
        </div>

        {error && <ErrorState message={error} />}
        {loading && <LoadingState label="Loading cases…" />}

        {!loading && visible.length === 0 && (
          <EmptyState
            title="No cases in this view"
            description={
              lowConfidenceOnly
                ? 'No low-confidence cases in the current filter.'
                : 'Ask a low-confidence or out-of-scope question as a User to see an escalation appear here.'
            }
          />
        )}

        <div className="space-y-4">
          {visible.map((c) => (
            <CaseCard key={c.id} item={c} onChanged={() => void load()} readOnly={isPlainUser} />
          ))}
        </div>
      </div>
    </AppWorkspaceShell>
  )
}
