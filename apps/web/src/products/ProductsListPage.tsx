import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { ApiError } from '../api/http'
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusBadge,
} from '../ui/primitives'
import {
  humanizeClassification,
  PRODUCT_CLASSIFICATIONS,
  Product,
  ProductClassification,
  productsApi,
} from '../api/productsApi'

function NewProductForm({ onCancel, onCreated }: { onCancel: () => void; onCreated: (p: Product) => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [classification, setClassification] = useState<ProductClassification | ''>('')
  const [jurisdiction, setJurisdiction] = useState<'india' | 'international' | ''>('')
  const [intendedUse, setIntendedUse] = useState('')
  const [developmentStage, setDevelopmentStage] = useState('')
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
      const product = await productsApi.create({
        name: name.trim(),
        description: description.trim() || null,
        product_classification: classification || null,
        jurisdiction: jurisdiction || null,
        intended_use: intendedUse.trim() || null,
        development_stage: developmentStage.trim() || null,
      })
      onCreated(product)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create product')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-4 border border-surface-border bg-white p-4" onSubmit={submit}>
      <h2 className="text-lg font-bold text-navy">Add product</h2>

      <div>
        <label className="gov-label" htmlFor="new-product-name">
          Name <span aria-hidden="true">*</span>
        </label>
        <input
          id="new-product-name"
          className="gov-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div>
        <label className="gov-label" htmlFor="new-product-description">
          Description
        </label>
        <textarea
          id="new-product-description"
          className="gov-input"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="gov-label" htmlFor="new-product-classification">
            Classification
          </label>
          <select
            id="new-product-classification"
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
          <label className="gov-label" htmlFor="new-product-jurisdiction">
            Jurisdiction
          </label>
          <select
            id="new-product-jurisdiction"
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
        <label className="gov-label" htmlFor="new-product-intended-use">
          Intended use
        </label>
        <input
          id="new-product-intended-use"
          className="gov-input"
          value={intendedUse}
          onChange={(e) => setIntendedUse(e.target.value)}
        />
      </div>

      <div>
        <label className="gov-label" htmlFor="new-product-stage">
          Development stage
        </label>
        <input
          id="new-product-stage"
          className="gov-input"
          value={developmentStage}
          onChange={(e) => setDevelopmentStage(e.target.value)}
          placeholder="e.g. research, prototype, market-ready"
        />
      </div>

      {error && <ErrorState message={error} />}

      <div className="flex flex-wrap gap-2">
        <button type="submit" className="gov-btn-primary" disabled={busy}>
          {busy ? 'Creating…' : 'Create product'}
        </button>
        <button type="button" className="gov-btn-secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  )
}

function ProductCard({ product, onOpen }: { product: Product; onOpen: () => void }) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      className="cursor-pointer space-y-3 border border-surface-border bg-white p-4 transition-colors hover:border-forest"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-lg font-bold text-navy">{product.name}</h2>
        <span className="text-xs text-ink-faint">
          Updated {new Date(product.updated_at).toLocaleDateString()}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <StatusBadge
          status={product.product_classification ? 'medium' : 'draft'}
          label={humanizeClassification(product.product_classification)}
        />
        <StatusBadge
          status={product.jurisdiction ? 'open' : 'draft'}
          label={
            product.jurisdiction === 'india'
              ? 'India'
              : product.jurisdiction === 'international'
                ? 'International'
                : 'Jurisdiction not set'
          }
        />
        {product.development_stage && (
          <StatusBadge status="in_progress" label={product.development_stage} />
        )}
      </div>
    </div>
  )
}

export default function ProductsListPage() {
  const navigate = useNavigate()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await productsApi.list()
      setProducts(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load products')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        <PageHeader
          title="My products"
          description="Each dossier tracks formulation, classification, pathways and Sahayak assessments in one place."
          actions={
            !showForm && products.length > 0 ? (
              <button type="button" className="gov-btn-primary" onClick={() => setShowForm(true)}>
                Add product
              </button>
            ) : undefined
          }
        />

        {showForm && (
          <NewProductForm
            onCancel={() => setShowForm(false)}
            onCreated={(p) => navigate(`/products/${p.id}`)}
          />
        )}

        {error && (
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

        {loading && <LoadingState label="Loading products…" />}

        {!loading && !error && products.length === 0 && !showForm && (
          <EmptyState
            title="No products yet"
            description="Create a dossier to track formulation, classification and IP/regulatory pathways."
            action={
              <button type="button" className="gov-btn-primary" onClick={() => setShowForm(true)}>
                Add product
              </button>
            }
          />
        )}

        {!loading && products.length > 0 && (
          <div className="space-y-3">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} onOpen={() => navigate(`/products/${p.id}`)} />
            ))}
          </div>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
