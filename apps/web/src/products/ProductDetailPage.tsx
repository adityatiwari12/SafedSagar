import { FormEvent, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'
import { ApiError } from '../api/http'
import { CaseItem } from '../api/casesApi'
import { StatusBadge, RiskBadge } from '../cases/caseBadges'
import {
  humanizeClassification,
  PRODUCT_CLASSIFICATIONS,
  Product,
  ProductClassification,
  productsApi,
} from '../api/productsApi'

const TABS = ['Overview', 'Formulation', 'Classification', 'Status', 'Assessments'] as const
type Tab = (typeof TABS)[number]

const LATER_PHASE_TABS = [
  'IP Strategy',
  'Prior Art',
  'Regulatory',
  'TK',
  'ABS',
  'Documents',
  'Activity',
] as const

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
    <form className="gov-panel space-y-4 p-4" onSubmit={submit}>
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

      {error && (
        <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

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
    <div className="gov-panel space-y-3 border-red-200 p-4">
      <p className="text-sm font-semibold text-red-900">
        Delete “{product.name}”? This cannot be undone.
      </p>
      {error && (
        <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="gov-btn-danger" onClick={() => void confirmDelete()} disabled={busy}>
          {busy ? 'Deleting…' : 'Yes, delete this product'}
        </button>
        <button type="button" className="gov-btn-secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  )
}

// Navigates to the chat page with a product-scoped draft seeded, mirroring
// ClassificationWizard's existing seededDraft precedent (navigate('/ask',
// { state: { seededDraft } })) plus an activeProduct so useChatSession
// includes productId on every turn while it's active.
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

function OverviewTab({ product }: { product: Product }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2 flex justify-end">
        <AskAboutProductButton product={product} />
      </div>
      <div className="sm:col-span-2">
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Description</dt>
        <dd className="mt-1 whitespace-pre-wrap text-sm text-ink">
          {product.description || 'No description yet.'}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Intended use</dt>
        <dd className="mt-1 text-sm text-ink">{product.intended_use || 'Not set'}</dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Target market</dt>
        <dd className="mt-1 text-sm text-ink">{product.target_market || 'Not set'}</dd>
      </div>
      <div className="sm:col-span-2">
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Claims</dt>
        <dd className="mt-1 whitespace-pre-wrap text-sm text-ink">{product.claims || 'Not set'}</dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Development stage
        </dt>
        <dd className="mt-1 text-sm text-ink">{product.development_stage || 'Not set'}</dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Created</dt>
        <dd className="mt-1 text-sm text-ink">{new Date(product.created_at).toLocaleString()}</dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Last updated</dt>
        <dd className="mt-1 text-sm text-ink">{new Date(product.updated_at).toLocaleString()}</dd>
      </div>
    </dl>
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
              <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-faint">
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
          <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
            Classification
          </dt>
          <dd className="mt-1 text-sm text-ink">
            {humanizeClassification(product.product_classification)}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
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
      <p className="rounded-sm border border-saffron/60 bg-orange-50 px-3 py-2 text-xs text-ink">
        This classification is generated to help route your query to the right IP/regulatory
        pathway. It is <span className="font-semibold">not a legal determination</span> — confirm
        against official sources or a qualified professional before relying on it for filings.
      </p>
    </div>
  )
}

function StatusSection({ title, status }: { title: string; status: Record<string, unknown> | null | undefined }) {
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
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
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

function StatusTab({ product }: { product: Product }) {
  return (
    <div className="space-y-6">
      <StatusSection title="IP status" status={product.ip_status} />
      <StatusSection title="Regulatory status" status={product.regulatory_status} />
      <StatusSection title="ABS / TK status" status={product.abs_tk_status} />
    </div>
  )
}

function AssessmentCard({ item }: { item: CaseItem }) {
  return (
    <div className="gov-panel space-y-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={item.status} />
          <RiskBadge risk={item.risk_level} />
        </div>
        <span className="text-xs text-ink-faint">{new Date(item.created_at).toLocaleString()}</span>
      </div>
      <p className="line-clamp-2 text-sm text-ink">{item.question}</p>
      <p className="text-xs text-ink-muted">
        Confidence: {item.confidence_level ?? 'n/a'}
        {item.confidence_score != null ? ` (${Math.round(item.confidence_score * 100)}%)` : ''}
      </p>
    </div>
  )
}

function AssessmentsTab({ product }: { product: Product }) {
  const [cases, setCases] = useState<CaseItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await productsApi.getCases(product.id)
      setCases(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load assessments')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product.id])

  if (loading) {
    return <p className="text-sm text-ink-muted">Loading assessments…</p>
  }

  if (error) {
    return (
      <div className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
        <p>{error}</p>
        <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
          Retry
        </button>
      </div>
    )
  }

  if (!cases || cases.length === 0) {
    return (
      <div className="gov-panel space-y-3 border-dashed p-6 text-center">
        <p className="text-sm text-ink-muted">No assessments yet for this product.</p>
        <div className="flex justify-center">
          <AskAboutProductButton product={product} />
        </div>
      </div>
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

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('Overview')
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)

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

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  return (
    <AppShell>
      <div className="space-y-5">
        {loading && <p className="text-sm text-ink-muted">Loading product…</p>}

        {!loading && notFound && (
          <div className="gov-panel border-dashed p-8 text-center">
            <p className="text-sm text-ink-muted">Not found or not yours.</p>
            <button type="button" className="gov-btn-secondary mt-4" onClick={() => navigate('/products')}>
              Back to my products
            </button>
          </div>
        )}

        {!loading && error && (
          <div className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
            <p>{error}</p>
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {!loading && product && !editing && !deleting && (
          <>
            <header className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-bold text-navy">{product.name}</h1>
                <p className="mt-1 text-sm text-ink-muted">
                  {humanizeClassification(product.product_classification)}
                  {product.jurisdiction ? ` · ${product.jurisdiction === 'india' ? 'India' : 'International'}` : ''}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="gov-btn-secondary" onClick={() => setEditing(true)}>
                  Edit
                </button>
                <button type="button" className="gov-btn-danger" onClick={() => setDeleting(true)}>
                  Delete
                </button>
              </div>
            </header>

            <div role="tablist" aria-label="Product dossier sections" className="flex flex-wrap gap-1 border-b border-line">
              {TABS.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="tab"
                  aria-selected={tab === t}
                  aria-current={tab === t ? 'true' : undefined}
                  onClick={() => setTab(t)}
                  className={`rounded-t-sm border-b-2 px-3 py-2 text-sm font-semibold ${
                    tab === t
                      ? 'border-saffron text-navy'
                      : 'border-transparent text-ink-muted hover:text-ink'
                  }`}
                >
                  {t}
                </button>
              ))}
              {LATER_PHASE_TABS.map((t) => (
                <button
                  key={t}
                  type="button"
                  disabled
                  title="Coming in a later phase"
                  className="cursor-not-allowed rounded-t-sm border-b-2 border-transparent px-3 py-2 text-sm font-semibold text-ink-faint/60"
                >
                  {t}
                </button>
              ))}
            </div>

            <div className="gov-panel p-4">
              {tab === 'Overview' && <OverviewTab product={product} />}
              {tab === 'Formulation' && <FormulationTab product={product} />}
              {tab === 'Classification' && <ClassificationTab product={product} />}
              {tab === 'Status' && <StatusTab product={product} />}
              {tab === 'Assessments' && <AssessmentsTab product={product} />}
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
    </AppShell>
  )
}
