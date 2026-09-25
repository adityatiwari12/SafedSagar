import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { ApiError } from '../api/http'
import { Product, productsApi } from '../api/productsApi'
import { CaseItem } from '../api/casesApi'
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from '../ui/primitives'
import { ipTypeInfo } from './ipTypeInfo'

interface ProjectOpportunities {
  product: Product
  cases: CaseItem[]
  ipTypes: Map<string, CaseItem> // ip_type -> most recent case that flagged it
}

async function loadOpportunities(): Promise<ProjectOpportunities[]> {
  const products = await productsApi.list()
  const perProduct = await Promise.all(
    products.map(async (product) => {
      const cases = await productsApi.getCases(product.id)
      const ipTypes = new Map<string, CaseItem>()
      // Cases already come back newest-first (see CasesPage) - keep the
      // first (most recent) case seen per ip_type as its representative.
      for (const c of cases) {
        for (const ipType of c.ip_types ?? []) {
          if (!ipTypes.has(ipType)) ipTypes.set(ipType, c)
        }
      }
      return { product, cases, ipTypes }
    }),
  )
  return perProduct
}

function ConfidenceDot({ level }: { level: string | null }) {
  if (!level) return null
  return <StatusBadge status={level} label={level} />
}

function ProjectOpportunityCard({ entry }: { entry: ProjectOpportunities }) {
  const { product, ipTypes } = entry
  const rows = [...ipTypes.entries()]

  return (
    <div className="space-y-3 border border-surface-border bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-navy">{product.name}</h2>
          {product.description && (
            <p className="mt-0.5 max-w-2xl text-sm text-ink-muted">{product.description}</p>
          )}
        </div>
        <Link
          to={`/products/${product.id}`}
          className="shrink-0 text-xs font-semibold text-forest underline-offset-2 hover:underline"
        >
          View project
        </Link>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-ink-faint">
          No IP regime has been identified for this project yet — ask a question about it in
          Research Sahayak to get started.
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {rows.map(([ipType, source]) => {
            const info = ipTypeInfo(ipType)
            return (
              <li key={ipType} className="border-l-2 border-saffron bg-ivory/50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-bold text-ink">{info.label}</p>
                  <ConfidenceDot level={source.confidence_level} />
                </div>
                {info.protects && (
                  <p className="mt-1 text-xs leading-relaxed text-ink-muted">{info.protects}</p>
                )}
                <p className="mt-2 text-[11px] italic text-ink-faint">
                  AI-identified from an assessment — confirm with an IP facilitator before acting.
                </p>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export default function IpOpportunitiesPage() {
  const [entries, setEntries] = useState<ProjectOpportunities[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setEntries(await loadOpportunities())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load IP opportunities')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const totalProjects = entries.length
  const withOpportunities = entries.filter((e) => e.ipTypes.size > 0).length

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        <PageHeader
          title="IP Opportunities"
          description="Which IP regimes your research projects have touched, based on Research Sahayak assessments already run against them — not a new analysis, a rollup of what's already been asked."
        />

        {error && (
          <div>
            <ErrorState message={error} />
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {loading && <LoadingState label="Loading IP opportunities…" />}

        {!loading && !error && totalProjects === 0 && (
          <EmptyState
            title="No research projects yet"
            description="Create a project under My Products, then ask Research Sahayak about it — identified IP regimes will show up here."
            action={
              <Link to="/products" className="gov-btn-primary !py-2 text-sm">
                Go to Research Projects
              </Link>
            }
          />
        )}

        {!loading && !error && totalProjects > 0 && (
          <>
            <p className="text-xs text-ink-faint">
              {withOpportunities} of {totalProjects} project{totalProjects === 1 ? '' : 's'} have at
              least one identified IP regime.
            </p>
            <div className="space-y-4">
              {entries.map((entry) => (
                <ProjectOpportunityCard key={entry.product.id} entry={entry} />
              ))}
            </div>
          </>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
