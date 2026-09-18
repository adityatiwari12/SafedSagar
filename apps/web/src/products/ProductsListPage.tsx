import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'
import { ApiError } from '../api/http'
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
    <form className="gov-panel space-y-4 p-4" onSubmit={submit}>
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
        />
      </div>

      {error && (
        <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

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
      className="gov-panel cursor-pointer space-y-2 p-4 transition-colors hover:border-saffron"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold text-navy">{product.name}</h2>
        <span className="text-xs text-ink-faint">
          Updated {new Date(product.updated_at).toLocaleDateString()}
        </span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-muted">
        <span>
          <span className="font-semibold text-ink">Classification:</span>{' '}
          {humanizeClassification(product.product_classification)}
        </span>
        <span>
          <span className="font-semibold text-ink">Jurisdiction:</span>{' '}
          {product.jurisdiction === 'india'
            ? 'India'
            : product.jurisdiction === 'international'
              ? 'International'
              : 'Not set'}
        </span>
        <span>
          <span className="font-semibold text-ink">Stage:</span>{' '}
          {product.development_stage || 'Not set'}
        </span>
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
    <AppShell>
      <div className="space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-navy">My products</h1>
            <p className="mt-1 text-sm text-ink-muted">
              Each product dossier tracks formulation, classification, and IP/regulatory/ABS status
              in one place.
            </p>
          </div>
          {!showForm && products.length > 0 && (
            <button type="button" className="gov-btn-primary" onClick={() => setShowForm(true)}>
              Add product
            </button>
          )}
        </header>

        {showForm && (
          <NewProductForm
            onCancel={() => setShowForm(false)}
            onCreated={(p) => navigate(`/products/${p.id}`)}
          />
        )}

        {error && (
          <div className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
            <p>{error}</p>
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {loading && <p className="text-sm text-ink-muted">Loading products…</p>}

        {!loading && !error && products.length === 0 && !showForm && (
          <div className="gov-panel border-dashed p-8 text-center">
            <p className="text-sm text-ink-muted">No products yet.</p>
            <button type="button" className="gov-btn-primary mt-4" onClick={() => setShowForm(true)}>
              Add product
            </button>
          </div>
        )}

        {!loading && products.length > 0 && (
          <div className="space-y-3">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} onOpen={() => navigate(`/products/${p.id}`)} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}
