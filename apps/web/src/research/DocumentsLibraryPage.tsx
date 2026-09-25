import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/http'
import { DocumentMeta, Product, productsApi } from '../api/productsApi'
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../ui/primitives'

function humanFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

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

function DocumentRow({ doc, productName }: { doc: DocumentMeta; productName: string | null }) {
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function download() {
    setError(null)
    setDownloading(true)
    try {
      const { blob, filename } = await productsApi.downloadDocument(doc.id)
      triggerBrowserDownload(blob, filename ?? doc.filename)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to download document')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <tr className="border-b border-line/60 align-top">
      <td className="py-2 pr-4 text-ink">{doc.filename}</td>
      <td className="py-2 pr-4 text-ink-muted">
        {productName ? (
          <Link to={`/products/${doc.product_id}`} className="text-forest hover:underline">
            {productName}
          </Link>
        ) : doc.case_id ? (
          <span>Linked case</span>
        ) : (
          <span className="text-ink-faint">—</span>
        )}
      </td>
      <td className="py-2 pr-4 text-ink-muted">{doc.doc_kind.replace(/_/g, ' ')}</td>
      <td className="py-2 pr-4 text-ink-muted">{humanFileSize(doc.size_bytes)}</td>
      <td className="py-2 pr-4 text-ink-muted">{new Date(doc.created_at).toLocaleDateString()}</td>
      <td className="py-2">
        <button
          type="button"
          className="gov-btn-secondary !py-1 text-xs"
          onClick={() => void download()}
          disabled={downloading}
        >
          {downloading ? 'Downloading…' : 'Download'}
        </button>
        {error && <p className="mt-1 text-[11px] text-red-700">{error}</p>}
      </td>
    </tr>
  )
}

export default function DocumentsLibraryPage() {
  const { user } = useAuth()
  // Only the 'user' role (entrepreneur + researcher personas) has
  // Permission.DOCUMENT_VIEW today - facilitator/regulatory_expert don't
  // (see app/authz/constants.py's ROLE_PERMISSIONS). Their nav still lists
  // "Documents" as a not-ready item pointing here, so branch before
  // calling an API that would 403, rather than showing a raw error.
  const supported = user?.role === 'user'
  const [documents, setDocuments] = useState<DocumentMeta[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(supported)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [docs, prods] = await Promise.all([
        productsApi.listAllDocuments(),
        productsApi.list(),
      ])
      setDocuments(docs)
      setProducts(prods)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (supported) void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const productNameById = new Map(products.map((p) => [p.id, p.name]))

  if (!supported) {
    return (
      <AppWorkspaceShell>
        <div className="space-y-5">
          <PageHeader
            title="Documents"
            description="A cross-case document library for this role is on the roadmap."
          />
          <EmptyState
            title="Not available for your role yet"
            description="A document library for facilitators/experts isn't built yet."
            action={
              <Link to="/cases" className="gov-btn-primary !py-2 text-sm">
                Go to Cases
              </Link>
            }
          />
        </div>
      </AppWorkspaceShell>
    )
  }

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        <PageHeader
          title="Documents"
          description="Every document you've uploaded across your research projects and cases, in one place."
        />

        {error && (
          <div>
            <ErrorState message={error} />
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {loading && <LoadingState label="Loading documents…" />}

        {!loading && !error && documents.length === 0 && (
          <EmptyState
            title="No documents yet"
            description="Upload a document from within a research project's Documents tab — it will show up here too."
            action={
              <Link to="/products" className="gov-btn-primary !py-2 text-sm">
                Go to Research Projects
              </Link>
            }
          />
        )}

        {!loading && !error && documents.length > 0 && (
          <div className="overflow-x-auto border border-surface-border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-ivory/80 text-[11px] uppercase tracking-wide text-ink-faint">
                <tr>
                  <th className="px-4 py-2">Filename</th>
                  <th className="px-4 py-2">Project</th>
                  <th className="px-4 py-2">Kind</th>
                  <th className="px-4 py-2">Size</th>
                  <th className="px-4 py-2">Uploaded</th>
                  <th className="px-4 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    doc={doc}
                    productName={doc.product_id ? productNameById.get(doc.product_id) ?? null : null}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
