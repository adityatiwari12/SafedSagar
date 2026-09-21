import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { ApiError } from '../api/http'
import { CaseItem } from '../api/casesApi'
import { StatusBadge as CaseStatusBadge, RiskBadge } from '../cases/caseBadges'
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Panel,
  StatusBadge,
} from '../ui/primitives'
import {
  humanizeClassification,
  PRODUCT_CLASSIFICATIONS,
  Product,
  ProductClassification,
  productsApi,
} from '../api/productsApi'

type TabId = 'overview' | 'formulation' | 'classification' | 'pathways' | 'assessments'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'formulation', label: 'Formulation' },
  { id: 'classification', label: 'Classification' },
  { id: 'pathways', label: 'Pathways' },
  { id: 'assessments', label: 'Assessments' },
]

const PLANNED_MODULES = [
  'IP Strategy',
  'Prior Art',
  'Regulatory detail',
  'TK',
  'ABS',
  'Documents',
  'Activity',
] as const

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

function OverviewTab({ product, latestCase }: { product: Product; latestCase: CaseItem | null }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-end gap-2">
        <AskAboutProductButton product={product} />
        <Link to="/classify" className="gov-btn-secondary">
          Classification wizard
        </Link>
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
          Deeper IP Strategy, Prior Art, Regulatory, TK, ABS, Documents and Activity views are
          staged for later phases. Current fields above remain the source of truth for MVP.
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
              {tab === 'overview' && <OverviewTab product={product} latestCase={latestCase} />}
              {tab === 'formulation' && <FormulationTab product={product} />}
              {tab === 'classification' && <ClassificationTab product={product} />}
              {tab === 'pathways' && <PathwaysTab product={product} />}
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
