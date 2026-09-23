import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { ApiError } from '../api/http'
import { CaseItem } from '../api/casesApi'
import { StatusBadge as CaseStatusBadge, RiskBadge } from '../cases/caseBadges'
import { useLanguage } from '../i18n/LanguageContext'
import type { TranslateFn } from '../i18n/types'
import {
  EmptyState,
  ErrorState,
  EvidenceList,
  LoadingState,
  PageHeader,
  Panel,
  StatusBadge,
} from '../ui/primitives'
import {
  ABS_ENTITY_CATEGORIES,
  ABS_ORIGINS,
  ABS_PURPOSES,
  ABS_SOURCINGS,
  AbsAssessment,
  AbsAssessmentInput,
  AbsEntityCategory,
  AbsOrigin,
  AbsPurpose,
  AbsSourcing,
  ComplianceEvidence,
  ComplianceItem,
  ComplianceItemPatch,
  ComplianceStatus,
  ComplianceSummary,
  COMPLIANCE_STATUSES,
  DOC_KINDS,
  DOCUMENT_MAX_UPLOAD_BYTES,
  DocKind,
  DocumentMeta,
  humanFileSize,
  humanizeArea,
  humanizeClassification,
  humanizeDocKind,
  PRODUCT_CLASSIFICATIONS,
  Product,
  ProductClassification,
  productsApi,
  summarizeCompliance,
} from '../api/productsApi'

type TabId =
  | 'overview'
  | 'formulation'
  | 'classification'
  | 'pathways'
  | 'compliance'
  | 'abs'
  | 'documents'
  | 'assessments'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'formulation', label: 'Formulation' },
  { id: 'classification', label: 'Classification' },
  { id: 'pathways', label: 'Pathways' },
  { id: 'compliance', label: 'Compliance' },
  { id: 'abs', label: 'ABS' },
  { id: 'documents', label: 'Documents' },
  { id: 'assessments', label: 'Assessments' },
]

/** Creates a temporary object URL and clicks a throwaway <a download> to
 * trigger a real browser download/open — used for both document downloads
 * and the report PDF, which both arrive as a Blob (not JSON) fetched with
 * the auth header via apiFetchBlob. */
function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

const COMPLIANCE_STATUS_TONE: Record<ComplianceStatus, string> = {
  unknown: 'draft',
  action_required: 'open',
  under_review: 'in_progress',
  complete: 'resolved',
  not_applicable: 'draft',
}

function complianceStatusLabel(statusValue: ComplianceStatus): string {
  return statusValue.replace(/_/g, ' ')
}

const PLANNED_MODULES = ['IP Strategy', 'Prior Art', 'Regulatory detail', 'TK', 'Activity'] as const

function statusSummary(status: Record<string, unknown> | null | undefined): string {
  if (!status || Object.keys(status).length === 0) return 'Not assessed'
  const preferred = ['status', 'stage', 'summary', 'level', 'state']
  for (const key of preferred) {
    if (status[key] != null && String(status[key]).trim()) return String(status[key])
  }
  const first = Object.values(status)[0]
  return first != null ? String(first) : 'Not assessed'
}

function deriveInsights(product: Product, latestCase: CaseItem | null) {
  const known: string[] = []
  const missing: string[] = []
  const routes: string[] = []
  const regulatory: string[] = []
  const tk: string[] = []
  const abs: string[] = []
  const actions: string[] = []

  if (product.description?.trim()) known.push('Product description recorded')
  else missing.push('Add a product description')

  if (product.product_classification) {
    known.push(`Classification: ${humanizeClassification(product.product_classification)}`)
  } else {
    missing.push('Run or set product classification')
    actions.push('Use Classify or Ask Sahayak to propose a pathway')
  }

  if (product.jurisdiction) {
    known.push(
      `Jurisdiction track: ${product.jurisdiction === 'india' ? 'India' : 'International'}`,
    )
  } else {
    missing.push('Set India or International jurisdiction')
  }

  if (product.development_stage?.trim()) known.push(`Stage: ${product.development_stage}`)
  else missing.push('Record development stage')

  if (product.intended_use?.trim()) known.push('Intended use captured')
  else missing.push('Capture intended use')

  if (product.claims?.trim()) known.push('Claims text on file')
  else missing.push('Document product claims')

  const ingredients = product.ingredients ?? []
  if (ingredients.length) known.push(`${ingredients.length} ingredient(s) listed`)
  else missing.push('List formulation ingredients')

  const bio = product.biological_resources ?? []
  if (bio.length) {
    known.push(`${bio.length} biological resource(s) noted`)
    abs.push('Biological resources present — ABS screening may apply')
    actions.push('Ask Sahayak about ABS obligations for listed biological resources')
  } else {
    missing.push('Note biological resources if any are used')
  }

  const cls = product.product_classification
  if (cls === 'classical_or_generic_medicine') {
    routes.push('Classical / generic pathway — patentability often constrained; verify Section 3(p) context')
  } else if (cls === 'patent_or_proprietary_medicine' || cls === 'new_or_non_classical_drug') {
    routes.push('Proprietary / novel composition may raise patent and AYUSH licensing questions')
  } else if (cls === 'ayurveda_aahara_or_nutraceutical') {
    routes.push('Ayurveda Aahara / nutraceutical regulatory track may apply (FSSAI)')
    regulatory.push('Check Ayurveda Aahara regulations and category lists')
  } else if (cls === 'cosmetic') {
    routes.push('Cosmetic regulatory pathway may be more relevant than drug IP')
  } else if (cls === 'phytopharmaceutical') {
    routes.push('Phytopharmaceutical route — confirm CDSCO / AYUSH boundary')
  }

  if (product.jurisdiction === 'international') {
    routes.push('International track — keep WIPO / destination-market rules separate from India filings')
  } else if (product.jurisdiction === 'india') {
    routes.push('India track — patents, GI, trademarks, ABS stay on domestic instruments')
  }

  if (product.ip_status && Object.keys(product.ip_status).length) {
    known.push(`IP status fields: ${Object.keys(product.ip_status).length}`)
  } else {
    missing.push('IP status not yet assessed')
  }

  if (product.regulatory_status && Object.keys(product.regulatory_status).length) {
    known.push('Regulatory status recorded')
  } else {
    missing.push('Regulatory status not yet assessed')
    regulatory.push('No regulatory assessment stored yet')
  }

  if (product.abs_tk_status && Object.keys(product.abs_tk_status).length) {
    const vals = Object.values(product.abs_tk_status).map(String).join(' ').toLowerCase()
    if (vals.includes('tk') || vals.includes('traditional')) {
      tk.push('TK-related status present in dossier — treat as indicator only')
    }
    if (vals.includes('abs') || vals.includes('biodiversity')) {
      abs.push('ABS-related status present in dossier')
    }
    known.push('ABS / TK status fields recorded')
  } else {
    missing.push('ABS / TK status not yet assessed')
    tk.push('No TK indicator stored yet (TKDL contents are never retrieved here)')
  }

  if (latestCase) {
    known.push('At least one Sahayak assessment linked')
    if (latestCase.confidence_level === 'low') {
      actions.push('Latest assessment has low confidence — consider facilitator review')
    } else {
      actions.push('Review latest assessment evidence before filing decisions')
    }
  } else {
    missing.push('No linked Sahayak assessments yet')
    actions.push('Ask about this product to generate a citation-grounded assessment')
  }

  if (!actions.length) actions.push('Keep dossier fields current as formulation evolves')

  return { known, missing, routes, regulatory, tk, abs, actions }
}

function AskAboutProductButton({ product, className }: { product: Product; className?: string }) {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      className={className ?? 'gov-btn-primary'}
      onClick={() =>
        navigate('/ask', {
          state: {
            seededDraft: `About my product "${product.name}": `,
            activeProduct: { id: product.id, name: product.name },
          },
        })
      }
    >
      Ask about this product
    </button>
  )
}

function DossierStatusStrip({
  product,
  latestCase,
}: {
  product: Product
  latestCase: CaseItem | null
}) {
  const confidence =
    latestCase?.confidence_level ?? (latestCase?.confidence_score != null ? 'assessed' : null)

  return (
    <div className="grid gap-2 border border-surface-border bg-white p-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      <StripCell label="Product" value={product.name} />
      <StripCell
        label="Classification"
        value={humanizeClassification(product.product_classification)}
      />
      <StripCell
        label="Jurisdiction"
        value={
          product.jurisdiction === 'india'
            ? 'India'
            : product.jurisdiction === 'international'
              ? 'International'
              : 'Not set'
        }
      />
      <StripCell label="Stage" value={product.development_stage || 'Not set'} />
      <StripCell label="IP status" value={statusSummary(product.ip_status)} />
      <StripCell label="Regulatory" value={statusSummary(product.regulatory_status)} />
      <div className="space-y-1">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">
          TK / ABS · AI confidence
        </p>
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge status="draft" label={statusSummary(product.abs_tk_status)} />
          <StatusBadge
            status={
              confidence === 'high'
                ? 'high'
                : confidence === 'medium'
                  ? 'medium'
                  : confidence === 'low'
                    ? 'low'
                    : 'insufficient'
            }
            label={confidence ? `AI: ${confidence}` : 'AI: not assessed'}
          />
        </div>
      </div>
    </div>
  )
}

function StripCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">{label}</p>
      <p className="mt-0.5 truncate text-sm font-semibold text-navy" title={value}>
        {value}
      </p>
    </div>
  )
}

function InsightsPanel({ product, latestCase }: { product: Product; latestCase: CaseItem | null }) {
  const insights = useMemo(() => deriveInsights(product, latestCase), [product, latestCase])

  return (
    <Panel title="Product insights">
      <p className="mb-4 text-xs text-ink-faint">
        Indicators only — not legal determinations. Confirm against official sources before filings.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <InsightList title="What is known" items={insights.known} />
        <InsightList title="What is missing" items={insights.missing} tone="warn" />
        <InsightList title="Potentially applicable IP routes" items={insights.routes} />
        <InsightList title="Potential regulatory requirements" items={insights.regulatory} />
        <InsightList title="TK indicators" items={insights.tk} />
        <InsightList title="ABS indicators" items={insights.abs} />
      </div>
      <div className="mt-4 border-t border-surface-border pt-4">
        <InsightList title="Recommended next actions" items={insights.actions} />
        <p className="mt-3 text-xs text-ink-muted">
          Expert review:{' '}
          {latestCase?.confidence_level === 'low'
            ? 'Latest assessment has low confidence — facilitator review recommended'
            : latestCase
              ? `Latest case status: ${latestCase.status.replace(/_/g, ' ')}`
              : 'No linked assessment yet'}
        </p>
      </div>
    </Panel>
  )
}

function InsightList({
  title,
  items,
  tone = 'default',
}: {
  title: string
  items: string[]
  tone?: 'default' | 'warn'
}) {
  return (
    <div>
      <h3
        className={`text-[11px] font-bold uppercase tracking-[0.12em] ${
          tone === 'warn' ? 'text-amber-900' : 'text-ink-faint'
        }`}
      >
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-ink-muted">None flagged yet.</p>
      ) : (
        <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-ink-muted">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function OverviewTab({
  product,
  latestCase,
  t,
  reportLoading,
  reportError,
  onDownloadReport,
}: {
  product: Product
  latestCase: CaseItem | null
  t: TranslateFn
  reportLoading: boolean
  reportError: string | null
  onDownloadReport: () => void
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <button
            type="button"
            className="gov-btn-primary"
            onClick={onDownloadReport}
            disabled={reportLoading}
          >
            {reportLoading ? t('report.generating') : t('report.download')}
          </button>
          {reportLoading && <p className="mt-1 text-xs text-ink-muted">{t('report.hint')}</p>}
          {reportError && <p className="mt-1 text-xs text-red-900">{reportError}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <AskAboutProductButton product={product} />
          <Link to="/classify" className="gov-btn-secondary">
            Classification wizard
          </Link>
        </div>
      </div>
      <InsightsPanel product={product} latestCase={latestCase} />
      <Panel title="Record summary">
        <dl className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <dt className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
              Description
            </dt>
            <dd className="mt-1 whitespace-pre-wrap text-sm text-ink">
              {product.description || 'No description yet.'}
            </dd>
          </div>
          <Field label="Intended use" value={product.intended_use} />
          <Field label="Target market" value={product.target_market} />
          <div className="sm:col-span-2">
            <Field label="Claims" value={product.claims} />
          </div>
          <Field label="Development stage" value={product.development_stage} />
          <Field label="Created" value={new Date(product.created_at).toLocaleString()} />
          <Field label="Last updated" value={new Date(product.updated_at).toLocaleString()} />
        </dl>
      </Panel>
    </div>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap text-sm text-ink">{value?.trim() || 'Not set'}</dd>
    </div>
  )
}

function FormulationTab({ product }: { product: Product }) {
  const ingredients = product.ingredients ?? []
  const bioResources = product.biological_resources ?? []
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold text-navy">Ingredients</h3>
        {ingredients.length === 0 ? (
          <p className="mt-2 text-sm text-ink-muted">No ingredients recorded yet.</p>
        ) : (
          <table className="mt-2 w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
                <th className="py-1.5 pr-4">Name</th>
                <th className="py-1.5">Quantity</th>
              </tr>
            </thead>
            <tbody>
              {ingredients.map((ing, i) => (
                <tr key={`${ing.name}-${i}`} className="border-b border-line/60">
                  <td className="py-1.5 pr-4 text-ink">{ing.name}</td>
                  <td className="py-1.5 text-ink-muted">{ing.quantity || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div>
        <h3 className="text-sm font-bold text-navy">Biological resources</h3>
        {bioResources.length === 0 ? (
          <p className="mt-2 text-sm text-ink-muted">No biological resources recorded yet.</p>
        ) : (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
            {bioResources.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function ClassificationTab({ product }: { product: Product }) {
  return (
    <div className="space-y-4">
      <dl className="grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
            Classification
          </dt>
          <dd className="mt-1">
            <StatusBadge
              status={product.product_classification ? 'medium' : 'draft'}
              label={humanizeClassification(product.product_classification)}
            />
          </dd>
        </div>
        <div>
          <dt className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
            Jurisdiction
          </dt>
          <dd className="mt-1 text-sm text-ink">
            {product.jurisdiction === 'india'
              ? 'India'
              : product.jurisdiction === 'international'
                ? 'International'
                : 'Not set'}
          </dd>
        </div>
      </dl>
      <p className="border border-saffron/50 bg-orange-50 px-3 py-2 text-xs text-ink">
        Classification helps route queries to the right IP/regulatory pathway. It is{' '}
        <span className="font-semibold">not a legal determination</span> — confirm against official
        sources or a qualified professional before filings.
      </p>
    </div>
  )
}

function StatusSection({
  title,
  status,
}: {
  title: string
  status: Record<string, unknown> | null | undefined
}) {
  const entries = status ? Object.entries(status) : []
  return (
    <div>
      <h3 className="text-sm font-bold text-navy">{title}</h3>
      {entries.length === 0 ? (
        <p className="mt-2 text-sm text-ink-muted">Not yet assessed.</p>
      ) : (
        <dl className="mt-2 grid gap-2 sm:grid-cols-2">
          {entries.map(([key, value]) => (
            <div key={key}>
              <dt className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                {key.replace(/_/g, ' ')}
              </dt>
              <dd className="mt-0.5 text-sm text-ink">{String(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}

function PathwaysTab({ product }: { product: Product }) {
  return (
    <div className="space-y-6">
      <StatusSection title="IP status" status={product.ip_status} />
      <StatusSection title="Regulatory status" status={product.regulatory_status} />
      <StatusSection title="ABS / TK status" status={product.abs_tk_status} />
      <div className="border border-dashed border-surface-border bg-ivory/50 px-4 py-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
          Planned pathway modules
        </p>
        <p className="mt-1 text-sm text-ink-muted">
          Deeper IP Strategy, Prior Art, Regulatory, TK and Activity views are staged for later
          phases. Current fields above remain the source of truth for MVP. See the ABS and
          Documents tabs for the modules now live.
        </p>
        <ul className="mt-2 flex flex-wrap gap-2">
          {PLANNED_MODULES.map((m) => (
            <li key={m}>
              <StatusBadge status="draft" label={m} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function ComplianceSummaryStrip({ summary }: { summary: ComplianceSummary }) {
  const { t } = useLanguage()
  const headline = t('compliance.summaryHeadline')
    .replace('{complete}', String(summary.complete))
    .replace('{total}', String(summary.total))
  const breakdown = COMPLIANCE_STATUSES.filter((s) => s !== 'complete' && summary[s] > 0)
  return (
    <div className="flex flex-wrap items-center gap-2 border border-surface-border bg-ivory/50 px-3 py-2">
      <StatusBadge status={COMPLIANCE_STATUS_TONE.complete} label={headline} />
      {breakdown.map((s) => (
        <StatusBadge
          key={s}
          status={COMPLIANCE_STATUS_TONE[s]}
          label={`${complianceStatusLabel(s)} · ${summary[s]}`}
        />
      ))}
    </div>
  )
}

function ComplianceEvidenceSection({ evidence }: { evidence: ComplianceEvidence[] | null | undefined }) {
  const { t } = useLanguage()
  if (!evidence || evidence.length === 0) return null
  return (
    <div className="border-t border-surface-border pt-2">
      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {t('compliance.evidenceLabel')}
      </p>
      <ul className="mt-1.5 space-y-1.5">
        {evidence.map((e, i) => (
          <li key={`${e.doc_id}-${i}`} className="text-xs text-ink-muted">
            <span className="font-semibold text-ink">{e.title}</span>
            {' — '}
            {[e.authority, e.section_or_article].filter(Boolean).join(' · ')}
            {e.source_url && (
              <>
                {' · '}
                <a
                  href={e.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-forest underline-offset-2 hover:underline"
                >
                  {t('compliance.viewSource')}
                </a>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ComplianceItemRow({
  item,
  onUpdate,
}: {
  item: ComplianceItem
  onUpdate: (itemId: string, patch: ComplianceItemPatch) => void
}) {
  const { t } = useLanguage()
  const [notesDraft, setNotesDraft] = useState(item.notes ?? '')
  const [notesDirty, setNotesDirty] = useState(false)

  useEffect(() => {
    if (!notesDirty) setNotesDraft(item.notes ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.notes, notesDirty])

  return (
    <article className="space-y-3 border border-surface-border bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold text-navy">{humanizeArea(item.area)}</h3>
            <StatusBadge
              status={COMPLIANCE_STATUS_TONE[item.status]}
              label={complianceStatusLabel(item.status)}
            />
          </div>
          <p className="mt-1 text-xs text-ink-muted">{item.applicability_reason}</p>
        </div>
        <div className="shrink-0">
          <label className="sr-only" htmlFor={`compliance-status-${item.id}`}>
            {t('compliance.statusLabel')}
          </label>
          <select
            id={`compliance-status-${item.id}`}
            className="gov-input !py-1 text-xs"
            value={item.status}
            onChange={(e) => onUpdate(item.id, { status: e.target.value as ComplianceStatus })}
          >
            {COMPLIANCE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {complianceStatusLabel(s)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="gov-label" htmlFor={`compliance-notes-${item.id}`}>
          {t('compliance.notesLabel')}
        </label>
        <textarea
          id={`compliance-notes-${item.id}`}
          className="gov-input"
          rows={2}
          placeholder={t('compliance.notesPlaceholder')}
          value={notesDraft}
          onChange={(e) => {
            setNotesDraft(e.target.value)
            setNotesDirty(true)
          }}
        />
        {notesDirty && (
          <button
            type="button"
            className="gov-btn-secondary mt-1 !py-1 text-xs"
            onClick={() => {
              onUpdate(item.id, { notes: notesDraft.trim() || null })
              setNotesDirty(false)
            }}
          >
            {t('compliance.saveNotes')}
          </button>
        )}
      </div>
      <ComplianceEvidenceSection evidence={item.evidence} />
    </article>
  )
}

function ComplianceTab({
  product,
  items,
  loading,
  error,
  generating,
  evidenceLoading,
  actionError,
  onRetry,
  onGenerate,
  onUpdateItem,
}: {
  product: Product
  items: ComplianceItem[] | null
  loading: boolean
  error: string | null
  generating: boolean
  evidenceLoading: boolean
  actionError: string | null
  onRetry: () => void
  onGenerate: (withEvidence: boolean) => void
  onUpdateItem: (itemId: string, patch: ComplianceItemPatch) => void
}) {
  const { t } = useLanguage()

  if (loading) return <LoadingState label={t('compliance.loading')} />
  if (error) {
    return (
      <div>
        <ErrorState message={error} />
        <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={onRetry}>
          {t('compliance.retry')}
        </button>
      </div>
    )
  }

  const summary = summarizeCompliance(items ?? [])
  const isEmpty = !items || items.length === 0
  const classification = product.product_classification

  const emptyDescription =
    !classification || classification === 'unclear'
      ? t('compliance.emptyBodyUnclassified')
      : classification === 'out_of_scope'
        ? t('compliance.emptyBodyOutOfScope')
        : t('compliance.emptyBodyGeneric')

  return (
    <div className="space-y-4">
      <p className="border border-saffron/50 bg-orange-50 px-3 py-2 text-xs text-ink">
        {t('compliance.disclaimer')}
      </p>

      {actionError && <ErrorState message={actionError} />}

      {isEmpty ? (
        <EmptyState
          title={t('compliance.emptyTitle')}
          description={emptyDescription}
          action={
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="gov-btn-primary"
                onClick={() => onGenerate(false)}
                disabled={generating}
              >
                {generating ? t('compliance.generating') : t('compliance.generate')}
              </button>
              {(!classification || classification === 'unclear') && (
                <Link to="/classify" className="gov-btn-secondary">
                  {t('compliance.classifyFirst')}
                </Link>
              )}
            </div>
          }
        />
      ) : (
        <>
          <ComplianceSummaryStrip summary={summary} />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button
              type="button"
              className="gov-btn-secondary !py-1.5 text-sm"
              onClick={() => onGenerate(false)}
              disabled={generating}
            >
              {generating ? t('compliance.generating') : t('compliance.refresh')}
            </button>
            <button
              type="button"
              className="gov-btn-secondary !py-1.5 text-sm"
              onClick={() => onGenerate(true)}
              disabled={evidenceLoading}
            >
              {evidenceLoading ? t('compliance.findingEvidence') : t('compliance.findEvidence')}
            </button>
          </div>
          {evidenceLoading && (
            <p className="text-xs text-ink-muted" role="status">
              {t('compliance.evidenceHint')}
            </p>
          )}
          <div className="space-y-3">
            {items!.map((item) => (
              <ComplianceItemRow key={item.id} item={item} onUpdate={onUpdateItem} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ABS tab
// ---------------------------------------------------------------------------

type AbsAnswers = Required<AbsAssessmentInput>

function answersFromAssessment(a: AbsAssessment): AbsAnswers {
  return {
    is_biological_resource: a.is_biological_resource,
    resource_description: a.resource_description,
    origin: a.origin,
    sourcing: a.sourcing,
    involves_traditional_knowledge: a.involves_traditional_knowledge,
    purpose: a.purpose,
    user_entity_category: a.user_entity_category,
  }
}

const ABS_STEPS = [
  'is_biological_resource',
  'resource_description',
  'origin',
  'sourcing',
  'involves_traditional_knowledge',
  'purpose',
  'user_entity_category',
] as const
type AbsStepId = (typeof ABS_STEPS)[number]

const ABS_ORIGIN_LABEL: Record<AbsOrigin, string> = {
  india: 'abs.originIndia',
  outside_india: 'abs.originOutsideIndia',
  unknown: 'abs.originUnknown',
}
const ABS_SOURCING_LABEL: Record<AbsSourcing, string> = {
  wild_collected: 'abs.sourcingWild',
  cultivated: 'abs.sourcingCultivated',
  both: 'abs.sourcingBoth',
  unknown: 'abs.sourcingUnknown',
}
const ABS_PURPOSE_LABEL: Record<AbsPurpose, string> = {
  commercial: 'abs.purposeCommercial',
  research_only: 'abs.purposeResearchOnly',
  unknown: 'abs.purposeUnknown',
}
const ABS_ENTITY_LABEL: Record<AbsEntityCategory, string> = {
  indian_individual: 'abs.entityIndianIndividual',
  indian_company: 'abs.entityIndianCompany',
  foreign_entity: 'abs.entityForeign',
  unknown: 'abs.entityUnknown',
}

function BooleanToggle({
  value,
  onChange,
  t,
}: {
  value: boolean | null
  onChange: (v: boolean | null) => void
  t: TranslateFn
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group">
      <button
        type="button"
        className={`gov-btn-secondary ${value === true ? '!border-forest !text-forest' : ''}`}
        aria-pressed={value === true}
        onClick={() => onChange(true)}
      >
        {t('abs.yes')}
      </button>
      <button
        type="button"
        className={`gov-btn-secondary ${value === false ? '!border-forest !text-forest' : ''}`}
        aria-pressed={value === false}
        onClick={() => onChange(false)}
      >
        {t('abs.no')}
      </button>
      <button
        type="button"
        className={`gov-btn-secondary ${value === null ? '!border-forest !text-forest' : ''}`}
        aria-pressed={value === null}
        onClick={() => onChange(null)}
      >
        {t('abs.notSure')}
      </button>
    </div>
  )
}

function AbsSelectStep<T extends string>({
  value,
  options,
  labelKeys,
  t,
  onChange,
}: {
  value: T | null
  options: readonly T[]
  labelKeys: Record<T, string>
  t: TranslateFn
  onChange: (v: T | null) => void
}) {
  return (
    <select
      id="abs-select-step"
      className="gov-input"
      value={value ?? ''}
      onChange={(e) => onChange((e.target.value || null) as T | null)}
    >
      <option value="">{t('abs.notAnsweredYet')}</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {t(labelKeys[opt] as Parameters<TranslateFn>[0])}
        </option>
      ))}
    </select>
  )
}

function AbsStepField({
  stepId,
  answers,
  update,
  t,
}: {
  stepId: AbsStepId
  answers: AbsAnswers
  update: <K extends keyof AbsAnswers>(key: K, value: AbsAnswers[K]) => void
  t: TranslateFn
}) {
  switch (stepId) {
    case 'is_biological_resource':
      return (
        <div>
          <label className="gov-label">{t('abs.qIsBiologicalResource')}</label>
          <BooleanToggle
            value={answers.is_biological_resource}
            onChange={(v) => update('is_biological_resource', v)}
            t={t}
          />
        </div>
      )
    case 'resource_description':
      return (
        <div>
          <label className="gov-label" htmlFor="abs-resource-description">
            {t('abs.qResourceDescription')}
          </label>
          <textarea
            id="abs-resource-description"
            className="gov-input"
            rows={3}
            placeholder={t('abs.resourceDescriptionPlaceholder')}
            value={answers.resource_description ?? ''}
            onChange={(e) => update('resource_description', e.target.value || null)}
          />
        </div>
      )
    case 'origin':
      return (
        <div>
          <label className="gov-label" htmlFor="abs-select-step">
            {t('abs.qOrigin')}
          </label>
          <AbsSelectStep
            value={answers.origin}
            options={ABS_ORIGINS}
            labelKeys={ABS_ORIGIN_LABEL}
            t={t}
            onChange={(v) => update('origin', v)}
          />
        </div>
      )
    case 'sourcing':
      return (
        <div>
          <label className="gov-label" htmlFor="abs-select-step">
            {t('abs.qSourcing')}
          </label>
          <AbsSelectStep
            value={answers.sourcing}
            options={ABS_SOURCINGS}
            labelKeys={ABS_SOURCING_LABEL}
            t={t}
            onChange={(v) => update('sourcing', v)}
          />
        </div>
      )
    case 'involves_traditional_knowledge':
      return (
        <div>
          <label className="gov-label">{t('abs.qInvolvesTk')}</label>
          <BooleanToggle
            value={answers.involves_traditional_knowledge}
            onChange={(v) => update('involves_traditional_knowledge', v)}
            t={t}
          />
        </div>
      )
    case 'purpose':
      return (
        <div>
          <label className="gov-label" htmlFor="abs-select-step">
            {t('abs.qPurpose')}
          </label>
          <AbsSelectStep
            value={answers.purpose}
            options={ABS_PURPOSES}
            labelKeys={ABS_PURPOSE_LABEL}
            t={t}
            onChange={(v) => update('purpose', v)}
          />
        </div>
      )
    case 'user_entity_category':
      return (
        <div>
          <label className="gov-label" htmlFor="abs-select-step">
            {t('abs.qEntityCategory')}
          </label>
          <AbsSelectStep
            value={answers.user_entity_category}
            options={ABS_ENTITY_CATEGORIES}
            labelKeys={ABS_ENTITY_LABEL}
            t={t}
            onChange={(v) => update('user_entity_category', v)}
          />
        </div>
      )
    default:
      return null
  }
}

function AbsWizard({
  initial,
  busy,
  error,
  t,
  onCancel,
  onSave,
}: {
  initial: AbsAnswers
  busy: boolean
  error: string | null
  t: TranslateFn
  onCancel?: () => void
  onSave: (answers: AbsAnswers) => Promise<void>
}) {
  const [answers, setAnswers] = useState<AbsAnswers>(initial)
  const [stepIndex, setStepIndex] = useState(0)
  const stepId = ABS_STEPS[stepIndex]
  const isLast = stepIndex === ABS_STEPS.length - 1

  function update<K extends keyof AbsAnswers>(key: K, value: AbsAnswers[K]) {
    setAnswers((prev) => ({ ...prev, [key]: value }))
  }

  async function save() {
    try {
      await onSave(answers)
    } catch {
      // error already surfaced via the `error` prop — stay on this step so
      // no earlier-step answer already in local state gets lost.
    }
  }

  return (
    <div className="space-y-4">
      <p className="border border-saffron/50 bg-orange-50 px-3 py-2 text-xs text-ink">
        {t('abs.disclaimer')}
      </p>
      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {t('abs.stepLabel')
          .replace('{step}', String(stepIndex + 1))
          .replace('{total}', String(ABS_STEPS.length))}
      </p>
      <AbsStepField stepId={stepId} answers={answers} update={update} t={t} />
      {error && <ErrorState message={error} />}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-surface-border pt-3">
        <div className="flex gap-2">
          <button
            type="button"
            className="gov-btn-secondary"
            onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
            disabled={stepIndex === 0 || busy}
          >
            {t('abs.back')}
          </button>
          {!isLast && (
            <button
              type="button"
              className="gov-btn-secondary"
              onClick={() => setStepIndex((i) => Math.min(ABS_STEPS.length - 1, i + 1))}
              disabled={busy}
            >
              {t('abs.next')}
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {onCancel && (
            <button type="button" className="gov-btn-secondary" onClick={onCancel} disabled={busy}>
              {t('abs.cancelEdit')}
            </button>
          )}
          <button
            type="button"
            className="gov-btn-primary"
            onClick={() => void save()}
            disabled={busy}
          >
            {busy ? t('abs.saving') : isLast ? t('abs.saveAssessment') : t('abs.saveAndExit')}
          </button>
        </div>
      </div>
    </div>
  )
}

const ABS_STATUS_TONE: Record<AbsAssessment['status'], string> = {
  not_started: 'draft',
  in_progress: 'in_progress',
  complete: 'resolved',
}

const ABS_STATUS_LABEL: Record<AbsAssessment['status'], string> = {
  not_started: 'abs.statusNotStarted',
  in_progress: 'abs.statusInProgress',
  complete: 'abs.statusComplete',
}

function AbsSummary({
  assessment,
  evidenceLoading,
  evidenceError,
  t,
  onEdit,
  onFindEvidence,
}: {
  assessment: AbsAssessment
  evidenceLoading: boolean
  evidenceError: string | null
  t: TranslateFn
  onEdit: () => void
  onFindEvidence: () => void
}) {
  const answers = answersFromAssessment(assessment)
  const yesNo = (v: boolean | null) => (v == null ? t('abs.notAnsweredYet') : v ? t('abs.yes') : t('abs.no'))
  const provisions = assessment.applicable_provisions ?? []

  return (
    <div className="space-y-4">
      <p className="border border-saffron/50 bg-orange-50 px-3 py-2 text-xs text-ink">
        {t('abs.disclaimer')}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge
          status={ABS_STATUS_TONE[assessment.status]}
          label={t(ABS_STATUS_LABEL[assessment.status] as Parameters<TranslateFn>[0])}
        />
        <button type="button" className="gov-btn-secondary !py-1.5 text-sm" onClick={onEdit}>
          {t('abs.editCta')}
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t('abs.qIsBiologicalResource')} value={yesNo(answers.is_biological_resource)} />
        <Field label={t('abs.qResourceDescription')} value={answers.resource_description} />
        <Field
          label={t('abs.qOrigin')}
          value={answers.origin ? t(ABS_ORIGIN_LABEL[answers.origin] as Parameters<TranslateFn>[0]) : null}
        />
        <Field
          label={t('abs.qSourcing')}
          value={answers.sourcing ? t(ABS_SOURCING_LABEL[answers.sourcing] as Parameters<TranslateFn>[0]) : null}
        />
        <Field label={t('abs.qInvolvesTk')} value={yesNo(answers.involves_traditional_knowledge)} />
        <Field
          label={t('abs.qPurpose')}
          value={answers.purpose ? t(ABS_PURPOSE_LABEL[answers.purpose] as Parameters<TranslateFn>[0]) : null}
        />
        <Field
          label={t('abs.qEntityCategory')}
          value={
            answers.user_entity_category
              ? t(ABS_ENTITY_LABEL[answers.user_entity_category] as Parameters<TranslateFn>[0])
              : null
          }
        />
      </div>
      <div className="border-t border-surface-border pt-3">
        <h3 className="text-sm font-bold text-navy">{t('abs.frameworkTitle')}</h3>
        <p className="mt-1 whitespace-pre-wrap text-sm text-ink">
          {assessment.preliminary_framework || t('abs.noFrameworkYet')}
        </p>
      </div>
      {assessment.next_steps && assessment.next_steps.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-navy">{t('abs.nextStepsTitle')}</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-ink-muted">
            {assessment.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="border-t border-surface-border pt-3">
        <button
          type="button"
          className="gov-btn-secondary !py-1.5 text-sm"
          onClick={onFindEvidence}
          disabled={evidenceLoading}
        >
          {evidenceLoading ? t('abs.findingEvidence') : t('abs.findEvidence')}
        </button>
        {evidenceLoading && (
          <p className="mt-2 text-xs text-ink-muted" role="status">
            {t('abs.evidenceHint')}
          </p>
        )}
        {evidenceError && <ErrorState message={evidenceError} />}
        {provisions.length > 0 ? (
          <div className="mt-3">
            <h3 className="text-sm font-bold text-navy">{t('abs.evidenceTitle')}</h3>
            <div className="mt-2">
              <EvidenceList
                items={provisions.map((p) => ({
                  title: p.title,
                  authority: p.authority ?? undefined,
                  provision: p.section_or_article ?? undefined,
                  sourceUrl: p.source_url ?? undefined,
                  docId: p.doc_id,
                }))}
              />
            </div>
          </div>
        ) : (
          !evidenceLoading && <p className="mt-2 text-xs text-ink-muted">{t('abs.evidenceEmpty')}</p>
        )}
      </div>
    </div>
  )
}

export function AbsTab({
  assessment,
  loading,
  error,
  saving,
  evidenceLoading,
  actionError,
  t,
  onRetry,
  onSave,
  onFindEvidence,
}: {
  assessment: AbsAssessment | null
  loading: boolean
  error: string | null
  saving: boolean
  evidenceLoading: boolean
  actionError: string | null
  t: TranslateFn
  onRetry: () => void
  onSave: (answers: AbsAnswers) => Promise<void>
  onFindEvidence: () => void
}) {
  const [editing, setEditing] = useState(false)

  if (loading) return <LoadingState label={t('abs.loading')} />
  if (error) {
    return (
      <div>
        <ErrorState message={error} />
        <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={onRetry}>
          {t('abs.retry')}
        </button>
      </div>
    )
  }
  if (!assessment) return null

  const hasSaved = assessment.id !== null
  const showWizard = !hasSaved || editing

  if (showWizard) {
    return (
      <AbsWizard
        key={assessment.updated_at ?? 'new'}
        initial={answersFromAssessment(assessment)}
        busy={saving}
        error={actionError}
        t={t}
        onCancel={hasSaved ? () => setEditing(false) : undefined}
        onSave={async (answers) => {
          await onSave(answers)
          setEditing(false)
        }}
      />
    )
  }

  return (
    <AbsSummary
      assessment={assessment}
      evidenceLoading={evidenceLoading}
      evidenceError={actionError}
      t={t}
      onEdit={() => setEditing(true)}
      onFindEvidence={onFindEvidence}
    />
  )
}

// ---------------------------------------------------------------------------
// Documents tab
// ---------------------------------------------------------------------------

const DOC_KIND_LABEL: Record<DocKind, string> = {
  label: 'documents.kindLabelDoc',
  certificate: 'documents.kindCertificate',
  formulation_sheet: 'documents.kindFormulationSheet',
  correspondence: 'documents.kindCorrespondence',
  other: 'documents.kindOther',
}

function DocumentUploadForm({
  productId,
  t,
  onUploaded,
}: {
  productId: string
  t: TranslateFn
  onUploaded: (doc: DocumentMeta) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [docKind, setDocKind] = useState<DocKind>('other')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const sizeWarning = file != null && file.size > DOCUMENT_MAX_UPLOAD_BYTES

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!file) return
    setError(null)
    setUploading(true)
    setProgress(0)
    try {
      const doc = await productsApi.uploadDocument({ file, docKind, productId }, setProgress)
      onUploaded(doc)
      setFile(null)
      const input = document.getElementById('document-upload-file') as HTMLInputElement | null
      if (input) input.value = ''
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <form className="space-y-3 border border-surface-border bg-ivory/40 p-4" onSubmit={submit}>
      <h3 className="text-sm font-bold text-navy">{t('documents.uploadTitle')}</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="gov-label" htmlFor="document-upload-file">
            {t('documents.fileLabel')}
          </label>
          <input
            id="document-upload-file"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            className="gov-input"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <div>
          <label className="gov-label" htmlFor="document-upload-kind">
            {t('documents.kindLabel')}
          </label>
          <select
            id="document-upload-kind"
            className="gov-input"
            value={docKind}
            onChange={(e) => setDocKind(e.target.value as DocKind)}
          >
            {DOC_KINDS.map((k) => (
              <option key={k} value={k}>
                {t(DOC_KIND_LABEL[k] as Parameters<TranslateFn>[0])}
              </option>
            ))}
          </select>
        </div>
      </div>
      <p className="text-xs text-ink-faint">{t('documents.uploadHintTypes')}</p>
      {sizeWarning && <p className="text-xs font-semibold text-amber-900">{t('documents.sizeWarning')}</p>}
      {error && <ErrorState message={error} />}
      {uploading && (
        <p className="text-xs text-ink-muted" role="status">
          {t('documents.uploading')} {progress}%
        </p>
      )}
      <button type="submit" className="gov-btn-primary !py-1.5 text-sm" disabled={!file || uploading}>
        {uploading ? t('documents.uploading') : t('documents.uploadButton')}
      </button>
    </form>
  )
}

function DocumentRow({
  doc,
  t,
  onDeleted,
}: {
  doc: DocumentMeta
  t: TranslateFn
  onDeleted: (id: string) => void
}) {
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function download() {
    setDownloadError(null)
    setDownloading(true)
    try {
      const { blob, filename } = await productsApi.downloadDocument(doc.id)
      triggerBrowserDownload(blob, filename ?? doc.filename)
    } catch (err) {
      setDownloadError(err instanceof ApiError ? err.message : 'Failed to download document')
    } finally {
      setDownloading(false)
    }
  }

  async function confirmDelete() {
    setDeleteError(null)
    setDeleting(true)
    try {
      await productsApi.removeDocument(doc.id)
      onDeleted(doc.id)
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Failed to delete document')
      setDeleting(false)
      setConfirming(false)
    }
  }

  return (
    <tr className="border-b border-line/60 align-top">
      <td className="py-2 pr-4 text-ink">{doc.filename}</td>
      <td className="py-2 pr-4 text-ink-muted">{humanizeDocKind(doc.doc_kind)}</td>
      <td className="py-2 pr-4 text-ink-muted">{humanFileSize(doc.size_bytes)}</td>
      <td className="py-2 pr-4 text-ink-muted">{new Date(doc.created_at).toLocaleDateString()}</td>
      <td className="py-2">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="gov-btn-secondary !py-1 text-xs"
            onClick={() => void download()}
            disabled={downloading}
          >
            {downloading ? t('documents.downloading') : t('documents.download')}
          </button>
          {!confirming ? (
            <button
              type="button"
              className="gov-btn-danger !py-1 text-xs"
              onClick={() => setConfirming(true)}
            >
              {t('documents.delete')}
            </button>
          ) : (
            <span className="flex flex-wrap items-center gap-1.5 text-xs">
              {t('documents.deleteConfirm')}
              <button
                type="button"
                className="gov-btn-danger !py-1 text-xs"
                onClick={() => void confirmDelete()}
                disabled={deleting}
              >
                {deleting ? t('documents.deleting') : t('documents.deleteConfirmYes')}
              </button>
              <button
                type="button"
                className="gov-btn-secondary !py-1 text-xs"
                onClick={() => setConfirming(false)}
                disabled={deleting}
              >
                {t('documents.deleteConfirmNo')}
              </button>
            </span>
          )}
        </div>
        {downloadError && <p className="mt-1 text-xs text-red-900">{downloadError}</p>}
        {deleteError && <p className="mt-1 text-xs text-red-900">{deleteError}</p>}
      </td>
    </tr>
  )
}

export function DocumentsTab({
  productId,
  documents,
  loading,
  error,
  t,
  onRetry,
  onUploaded,
  onDeleted,
}: {
  productId: string
  documents: DocumentMeta[] | null
  loading: boolean
  error: string | null
  t: TranslateFn
  onRetry: () => void
  onUploaded: (doc: DocumentMeta) => void
  onDeleted: (id: string) => void
}) {
  if (loading) return <LoadingState label={t('documents.loading')} />
  if (error) {
    return (
      <div>
        <ErrorState message={error} />
        <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={onRetry}>
          {t('documents.retry')}
        </button>
      </div>
    )
  }

  const isEmpty = !documents || documents.length === 0

  return (
    <div className="space-y-4">
      <DocumentUploadForm productId={productId} t={t} onUploaded={onUploaded} />
      {isEmpty ? (
        <EmptyState title={t('documents.emptyTitle')} description={t('documents.emptyBody')} />
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
              <th className="py-1.5 pr-4">{t('documents.filenameHeader')}</th>
              <th className="py-1.5 pr-4">{t('documents.kindHeader')}</th>
              <th className="py-1.5 pr-4">{t('documents.sizeHeader')}</th>
              <th className="py-1.5 pr-4">{t('documents.uploadedHeader')}</th>
              <th className="py-1.5">{t('documents.actionsHeader')}</th>
            </tr>
          </thead>
          <tbody>
            {documents!.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} t={t} onDeleted={onDeleted} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function AssessmentCard({ item }: { item: CaseItem }) {
  return (
    <article className="space-y-2 border border-surface-border bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <CaseStatusBadge status={item.status} />
          <RiskBadge risk={item.risk_level} />
        </div>
        <span className="text-xs text-ink-faint">{new Date(item.created_at).toLocaleString()}</span>
      </div>
      <p className="line-clamp-2 text-sm text-ink">{item.question}</p>
      <p className="text-xs text-ink-muted">
        Confidence: {item.confidence_level ?? 'n/a'}
        {item.confidence_score != null ? ` (${Math.round(item.confidence_score * 100)}%)` : ''}
      </p>
    </article>
  )
}

function AssessmentsTab({
  product,
  cases,
  loading,
  error,
  onRetry,
}: {
  product: Product
  cases: CaseItem[] | null
  loading: boolean
  error: string | null
  onRetry: () => void
}) {
  if (loading) return <LoadingState label="Loading assessments…" />
  if (error) {
    return (
      <div>
        <ErrorState message={error} />
        <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={onRetry}>
          Retry
        </button>
      </div>
    )
  }
  if (!cases || cases.length === 0) {
    return (
      <EmptyState
        title="No assessments yet"
        description="Ask Sahayak about this product to generate a citation-grounded assessment."
        action={<AskAboutProductButton product={product} />}
      />
    )
  }
  return (
    <div className="space-y-3">
      {cases.map((c) => (
        <AssessmentCard key={c.id} item={c} />
      ))}
    </div>
  )
}

function EditForm({
  product,
  onCancel,
  onSaved,
}: {
  product: Product
  onCancel: () => void
  onSaved: (p: Product) => void
}) {
  const [name, setName] = useState(product.name)
  const [description, setDescription] = useState(product.description ?? '')
  const [classification, setClassification] = useState<ProductClassification | ''>(
    product.product_classification ?? '',
  )
  const [jurisdiction, setJurisdiction] = useState<'india' | 'international' | ''>(
    product.jurisdiction ?? '',
  )
  const [intendedUse, setIntendedUse] = useState(product.intended_use ?? '')
  const [claims, setClaims] = useState(product.claims ?? '')
  const [targetMarket, setTargetMarket] = useState(product.target_market ?? '')
  const [developmentStage, setDevelopmentStage] = useState(product.development_stage ?? '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Product name is required.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const updated = await productsApi.update(product.id, {
        name: name.trim(),
        description: description.trim() || null,
        product_classification: classification || null,
        jurisdiction: jurisdiction || null,
        intended_use: intendedUse.trim() || null,
        claims: claims.trim() || null,
        target_market: targetMarket.trim() || null,
        development_stage: developmentStage.trim() || null,
      })
      onSaved(updated)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to save changes')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-4 border border-surface-border bg-white p-4" onSubmit={submit}>
      <h2 className="text-lg font-bold text-navy">Edit product</h2>
      <div>
        <label className="gov-label" htmlFor="edit-product-name">
          Name <span aria-hidden="true">*</span>
        </label>
        <input
          id="edit-product-name"
          className="gov-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="gov-label" htmlFor="edit-product-description">
          Description
        </label>
        <textarea
          id="edit-product-description"
          className="gov-input"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="gov-label" htmlFor="edit-product-classification">
            Classification
          </label>
          <select
            id="edit-product-classification"
            className="gov-input"
            value={classification}
            onChange={(e) => setClassification(e.target.value as ProductClassification | '')}
          >
            <option value="">Not yet classified</option>
            {PRODUCT_CLASSIFICATIONS.map((c) => (
              <option key={c} value={c}>
                {humanizeClassification(c)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="gov-label" htmlFor="edit-product-jurisdiction">
            Jurisdiction
          </label>
          <select
            id="edit-product-jurisdiction"
            className="gov-input"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value as 'india' | 'international' | '')}
          >
            <option value="">Not set</option>
            <option value="india">India</option>
            <option value="international">International</option>
          </select>
        </div>
      </div>
      <div>
        <label className="gov-label" htmlFor="edit-product-intended-use">
          Intended use
        </label>
        <input
          id="edit-product-intended-use"
          className="gov-input"
          value={intendedUse}
          onChange={(e) => setIntendedUse(e.target.value)}
        />
      </div>
      <div>
        <label className="gov-label" htmlFor="edit-product-claims">
          Claims
        </label>
        <textarea
          id="edit-product-claims"
          className="gov-input"
          rows={3}
          value={claims}
          onChange={(e) => setClaims(e.target.value)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="gov-label" htmlFor="edit-product-target-market">
            Target market
          </label>
          <input
            id="edit-product-target-market"
            className="gov-input"
            value={targetMarket}
            onChange={(e) => setTargetMarket(e.target.value)}
          />
        </div>
        <div>
          <label className="gov-label" htmlFor="edit-product-stage">
            Development stage
          </label>
          <input
            id="edit-product-stage"
            className="gov-input"
            value={developmentStage}
            onChange={(e) => setDevelopmentStage(e.target.value)}
          />
        </div>
      </div>
      {error && <ErrorState message={error} />}
      <div className="flex flex-wrap gap-2">
        <button type="submit" className="gov-btn-primary" disabled={busy}>
          {busy ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" className="gov-btn-secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  )
}

function DeleteConfirm({
  product,
  onCancel,
  onDeleted,
}: {
  product: Product
  onCancel: () => void
  onDeleted: () => void
}) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function confirmDelete() {
    setBusy(true)
    setError(null)
    try {
      await productsApi.remove(product.id)
      onDeleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to delete product')
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 border border-red-200 bg-white p-4">
      <p className="text-sm font-semibold text-red-900">
        Delete “{product.name}”? This cannot be undone.
      </p>
      {error && <ErrorState message={error} />}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="gov-btn-danger"
          onClick={() => void confirmDelete()}
          disabled={busy}
        >
          {busy ? 'Deleting…' : 'Yes, delete this product'}
        </button>
        <button type="button" className="gov-btn-secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabId>('overview')
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [cases, setCases] = useState<CaseItem[] | null>(null)
  const [casesLoading, setCasesLoading] = useState(true)
  const [casesError, setCasesError] = useState<string | null>(null)
  const [complianceItems, setComplianceItems] = useState<ComplianceItem[] | null>(null)
  const [complianceLoading, setComplianceLoading] = useState(true)
  const [complianceError, setComplianceError] = useState<string | null>(null)
  const [complianceGenerating, setComplianceGenerating] = useState(false)
  const [complianceEvidenceLoading, setComplianceEvidenceLoading] = useState(false)
  const [complianceActionError, setComplianceActionError] = useState<string | null>(null)
  const [absAssessment, setAbsAssessment] = useState<AbsAssessment | null>(null)
  const [absLoading, setAbsLoading] = useState(true)
  const [absError, setAbsError] = useState<string | null>(null)
  const [absSaving, setAbsSaving] = useState(false)
  const [absEvidenceLoading, setAbsEvidenceLoading] = useState(false)
  const [absActionError, setAbsActionError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<DocumentMeta[] | null>(null)
  const [documentsLoading, setDocumentsLoading] = useState(true)
  const [documentsError, setDocumentsError] = useState<string | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const { t } = useLanguage()

  async function load() {
    if (!id) return
    setLoading(true)
    setError(null)
    setNotFound(false)
    try {
      const data = await productsApi.get(id)
      setProduct(data)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 404)) {
        setNotFound(true)
      } else {
        setError(err instanceof ApiError ? err.message : 'Failed to load product')
      }
    } finally {
      setLoading(false)
    }
  }

  async function loadCases(productId: string) {
    setCasesLoading(true)
    setCasesError(null)
    try {
      const data = await productsApi.getCases(productId)
      setCases(data)
    } catch (err) {
      setCasesError(err instanceof ApiError ? err.message : 'Failed to load assessments')
    } finally {
      setCasesLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (product?.id) void loadCases(product.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id])

  async function loadCompliance(productId: string) {
    setComplianceLoading(true)
    setComplianceError(null)
    try {
      const data = await productsApi.getCompliance(productId)
      setComplianceItems(data.items)
    } catch (err) {
      setComplianceError(
        err instanceof ApiError ? err.message : 'Failed to load compliance checklist',
      )
    } finally {
      setComplianceLoading(false)
    }
  }

  useEffect(() => {
    if (product?.id) void loadCompliance(product.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id])

  async function handleGenerateCompliance(withEvidence: boolean) {
    if (!product) return
    setComplianceActionError(null)
    if (withEvidence) setComplianceEvidenceLoading(true)
    else setComplianceGenerating(true)
    try {
      const data = await productsApi.generateCompliance(product.id, withEvidence)
      setComplianceItems(data.items)
    } catch (err) {
      setComplianceActionError(
        err instanceof ApiError ? err.message : 'Failed to generate compliance checklist',
      )
    } finally {
      if (withEvidence) setComplianceEvidenceLoading(false)
      else setComplianceGenerating(false)
    }
  }

  async function handleUpdateComplianceItem(itemId: string, patch: ComplianceItemPatch) {
    if (!product || !complianceItems) return
    const previous = complianceItems
    setComplianceActionError(null)
    setComplianceItems(previous.map((i) => (i.id === itemId ? { ...i, ...patch } : i)))
    try {
      const updated = await productsApi.updateComplianceItem(product.id, itemId, patch)
      setComplianceItems((cur) => (cur ? cur.map((i) => (i.id === itemId ? updated : i)) : cur))
    } catch (err) {
      setComplianceItems(previous)
      setComplianceActionError(
        err instanceof ApiError ? err.message : 'Failed to update checklist item',
      )
    }
  }

  async function loadAbs(productId: string) {
    setAbsLoading(true)
    setAbsError(null)
    try {
      const data = await productsApi.getAbsAssessment(productId)
      setAbsAssessment(data)
    } catch (err) {
      setAbsError(err instanceof ApiError ? err.message : 'Failed to load ABS assessment')
    } finally {
      setAbsLoading(false)
    }
  }

  useEffect(() => {
    if (product?.id) void loadAbs(product.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id])

  /** Always sends the complete current answer set (PUT is a full replace
   * server-side), whether called from the wizard's final save or from the
   * summary's "Find supporting sources" re-run on the already-saved
   * answers. */
  async function handleSaveAbs(answers: AbsAssessmentInput, withEvidence: boolean) {
    if (!product) return
    setAbsActionError(null)
    if (withEvidence) setAbsEvidenceLoading(true)
    else setAbsSaving(true)
    try {
      const updated = await productsApi.saveAbsAssessment(product.id, answers, withEvidence)
      setAbsAssessment(updated)
    } catch (err) {
      setAbsActionError(err instanceof ApiError ? err.message : 'Failed to save ABS assessment')
      throw err
    } finally {
      if (withEvidence) setAbsEvidenceLoading(false)
      else setAbsSaving(false)
    }
  }

  async function handleFindAbsEvidence() {
    if (!absAssessment) return
    try {
      await handleSaveAbs(answersFromAssessment(absAssessment), true)
    } catch {
      // error already surfaced via absActionError
    }
  }

  async function loadDocuments(productId: string) {
    setDocumentsLoading(true)
    setDocumentsError(null)
    try {
      const data = await productsApi.listDocuments(productId)
      setDocuments(data)
    } catch (err) {
      setDocumentsError(err instanceof ApiError ? err.message : 'Failed to load documents')
    } finally {
      setDocumentsLoading(false)
    }
  }

  useEffect(() => {
    if (product?.id) void loadDocuments(product.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id])

  async function handleDownloadReport() {
    if (!product) return
    setReportError(null)
    setReportLoading(true)
    try {
      const { blob, filename } = await productsApi.downloadReport(product.id)
      triggerBrowserDownload(blob, filename ?? `${product.name}-assessment-report.pdf`)
    } catch (err) {
      setReportError(err instanceof ApiError ? err.message : 'Failed to generate report')
    } finally {
      setReportLoading(false)
    }
  }

  const latestCase = cases?.[0] ?? null

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        {loading && <LoadingState label="Loading product dossier…" />}

        {!loading && notFound && (
          <EmptyState
            title="Not found or not yours"
            description="This product dossier is unavailable for your account."
            action={
              <button type="button" className="gov-btn-secondary" onClick={() => navigate('/products')}>
                Back to my products
              </button>
            }
          />
        )}

        {!loading && error && (
          <div>
            <ErrorState message={error} />
            <button
              type="button"
              className="gov-btn-secondary mt-2 !py-1 text-xs"
              onClick={() => void load()}
            >
              Retry
            </button>
          </div>
        )}

        {!loading && product && !editing && !deleting && (
          <>
            <PageHeader
              title={product.name}
              description="Product dossier — formulation, classification, pathways and Sahayak assessments."
              breadcrumb={
                <Link to="/products" className="hover:underline">
                  My products
                </Link>
              }
              actions={
                <>
                  <AskAboutProductButton product={product} className="gov-btn-primary !py-1.5 text-sm" />
                  <button type="button" className="gov-btn-secondary" onClick={() => setEditing(true)}>
                    Edit
                  </button>
                  <button type="button" className="gov-btn-danger" onClick={() => setDeleting(true)}>
                    Delete
                  </button>
                </>
              }
            />

            <DossierStatusStrip product={product} latestCase={latestCase} />

            <div
              role="tablist"
              aria-label="Product dossier sections"
              className="flex flex-wrap gap-1 border-b border-line"
            >
              {TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  aria-current={tab === t.id ? 'true' : undefined}
                  onClick={() => setTab(t.id)}
                  className={`border-b-2 px-3 py-2 text-sm font-semibold ${
                    tab === t.id
                      ? 'border-saffron text-navy'
                      : 'border-transparent text-ink-muted hover:text-ink'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="border border-surface-border bg-white p-4">
              {tab === 'overview' && (
                <OverviewTab
                  product={product}
                  latestCase={latestCase}
                  t={t}
                  reportLoading={reportLoading}
                  reportError={reportError}
                  onDownloadReport={() => void handleDownloadReport()}
                />
              )}
              {tab === 'formulation' && <FormulationTab product={product} />}
              {tab === 'classification' && <ClassificationTab product={product} />}
              {tab === 'pathways' && <PathwaysTab product={product} />}
              {tab === 'compliance' && (
                <ComplianceTab
                  product={product}
                  items={complianceItems}
                  loading={complianceLoading}
                  error={complianceError}
                  generating={complianceGenerating}
                  evidenceLoading={complianceEvidenceLoading}
                  actionError={complianceActionError}
                  onRetry={() => void loadCompliance(product.id)}
                  onGenerate={(withEvidence) => void handleGenerateCompliance(withEvidence)}
                  onUpdateItem={(itemId, patch) => void handleUpdateComplianceItem(itemId, patch)}
                />
              )}
              {tab === 'abs' && (
                <AbsTab
                  assessment={absAssessment}
                  loading={absLoading}
                  error={absError}
                  saving={absSaving}
                  evidenceLoading={absEvidenceLoading}
                  actionError={absActionError}
                  t={t}
                  onRetry={() => void loadAbs(product.id)}
                  onSave={(answers) => handleSaveAbs(answers, false)}
                  onFindEvidence={() => void handleFindAbsEvidence()}
                />
              )}
              {tab === 'documents' && (
                <DocumentsTab
                  productId={product.id}
                  documents={documents}
                  loading={documentsLoading}
                  error={documentsError}
                  t={t}
                  onRetry={() => void loadDocuments(product.id)}
                  onUploaded={(doc) => setDocuments((cur) => (cur ? [doc, ...cur] : [doc]))}
                  onDeleted={(docId) =>
                    setDocuments((cur) => (cur ? cur.filter((d) => d.id !== docId) : cur))
                  }
                />
              )}
              {tab === 'assessments' && (
                <AssessmentsTab
                  product={product}
                  cases={cases}
                  loading={casesLoading}
                  error={casesError}
                  onRetry={() => void loadCases(product.id)}
                />
              )}
            </div>
          </>
        )}

        {!loading && product && editing && (
          <EditForm
            product={product}
            onCancel={() => setEditing(false)}
            onSaved={(p) => {
              setProduct(p)
              setEditing(false)
            }}
          />
        )}

        {!loading && product && deleting && (
          <DeleteConfirm
            product={product}
            onCancel={() => setDeleting(false)}
            onDeleted={() => navigate('/products')}
          />
        )}
      </div>
    </AppWorkspaceShell>
  )
}
