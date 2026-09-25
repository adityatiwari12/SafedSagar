import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { useLanguage } from '../i18n/LanguageContext'
import { ApiError } from '../api/http'
import { AbsAssessment, Product, productsApi } from '../api/productsApi'
import {
  EmptyState,
  ErrorState,
  EvidenceList,
  LoadingState,
  PageHeader,
  StatusBadge,
} from '../ui/primitives'

interface ProjectAbs {
  product: Product
  assessment: AbsAssessment | null
}

const STATUS_TONE: Record<string, string> = {
  not_started: 'draft',
  in_progress: 'in_progress',
  complete: 'resolved',
}

async function loadAbsExplorer(): Promise<ProjectAbs[]> {
  const products = await productsApi.list()
  return Promise.all(
    products.map(async (product) => {
      try {
        const assessment = await productsApi.getAbsAssessment(product.id)
        return { product, assessment }
      } catch {
        return { product, assessment: null }
      }
    }),
  )
}

function ProjectAbsCard({ entry }: { entry: ProjectAbs }) {
  const { t } = useLanguage()
  const { product, assessment } = entry
  const status = assessment?.status ?? 'not_started'
  const provisions =
    assessment?.applicable_provisions?.map((p) => ({
      title: p.title,
      authority: p.authority ?? undefined,
      provision: p.section_or_article ?? undefined,
      sourceUrl: p.source_url ?? undefined,
      docId: p.doc_id,
    })) ?? []

  return (
    <div className="space-y-3 border border-surface-border bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-navy">{product.name}</h2>
          {assessment?.is_biological_resource && (
            <p className="mt-0.5 text-xs text-ink-muted">
              Uses a biological resource — ABS approval may be required.
            </p>
          )}
          {assessment?.involves_traditional_knowledge && (
            <p className="mt-0.5 text-xs text-ink-muted">{t('chat.absTk')}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <StatusBadge status={STATUS_TONE[status] ?? 'draft'} label={status.replace(/_/g, ' ')} />
          <Link
            to={`/products/${product.id}`}
            className="text-xs font-semibold text-forest underline-offset-2 hover:underline"
          >
            {status === 'not_started' ? 'Start assessment' : 'View project'}
          </Link>
        </div>
      </div>

      {provisions.length > 0 && (
        <div className="border-t border-surface-border pt-3">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-faint">
            Applicable provisions
          </h3>
          <EvidenceList items={provisions} />
        </div>
      )}
    </div>
  )
}

export default function TkAbsExplorerPage() {
  const [entries, setEntries] = useState<ProjectAbs[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setEntries(await loadAbsExplorer())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load TK & ABS explorer')
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
          title="TK & ABS Explorer"
          description="Traditional-knowledge and biodiversity/ABS status across your research projects, sourced from each project's ABS assessment — not a new analysis."
        />

        <p className="border border-saffron/50 bg-orange-50 px-3 py-2 text-xs text-ink">
          TKDL is awareness-only here — its database contents are never retrieved (NDA-restricted
          access). A traditional-knowledge indicator means prior art may exist there; contact the
          CSIR-TKDL unit directly to check.
        </p>

        {error && (
          <div>
            <ErrorState message={error} />
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {loading && <LoadingState label="Loading TK & ABS explorer…" />}

        {!loading && !error && entries.length === 0 && (
          <EmptyState
            title="No research projects yet"
            description="Create a project under My Products, then run its ABS assessment — status will show up here."
            action={
              <Link to="/products" className="gov-btn-primary !py-2 text-sm">
                Go to Research Projects
              </Link>
            }
          />
        )}

        {!loading && !error && entries.length > 0 && (
          <div className="space-y-4">
            {entries.map((entry) => (
              <ProjectAbsCard key={entry.product.id} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
