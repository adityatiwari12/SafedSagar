import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { UserRole } from '../api/authApi'
import { casesApi } from '../api/casesApi'
import { productsApi } from '../api/productsApi'
import { adminApi } from '../api/adminApi'
import { Panel } from '../ui/primitives'

function Stat({ label, value, to }: { label: string; value: string | number; to?: string }) {
  const body = (
    <>
      <p className="text-2xl font-extrabold text-navy">{value}</p>
      <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-ink-faint">{label}</p>
    </>
  )
  if (!to) return <div>{body}</div>
  return (
    <Link to={to} className="block hover:opacity-80">
      {body}
    </Link>
  )
}

/** Facilitator/Regulatory Expert: their real open-case-queue breakdown -
 * same data CasesPage's AttentionSummary shows, surfaced one click
 * earlier. No new endpoint - reuses casesApi.list(). */
function CaseQueueGlance() {
  const [counts, setCounts] = useState<{ open: number; lowConfidence: number } | null>(null)

  useEffect(() => {
    let cancelled = false
    casesApi
      .list('open')
      .then((cases) => {
        if (cancelled) return
        setCounts({
          open: cases.length,
          lowConfidence: cases.filter((c) => c.confidence_level === 'low').length,
        })
      })
      .catch(() => {
        if (!cancelled) setCounts({ open: 0, lowConfidence: 0 })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Panel title="At a glance">
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Open cases" value={counts?.open ?? '—'} to="/cases" />
        <Stat label="Low confidence" value={counts?.lowConfidence ?? '—'} to="/cases" />
      </div>
    </Panel>
  )
}

/** User / Researcher persona: their own product/research-project count
 * and how many are missing basic classification - reuses productsApi.list(). */
function ProductsGlance() {
  const [counts, setCounts] = useState<{ total: number; unclassified: number } | null>(null)

  useEffect(() => {
    let cancelled = false
    productsApi
      .list()
      .then((products) => {
        if (cancelled) return
        setCounts({
          total: products.length,
          unclassified: products.filter((p) => !p.product_classification).length,
        })
      })
      .catch(() => {
        if (!cancelled) setCounts({ total: 0, unclassified: 0 })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Panel title="At a glance">
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Research projects" value={counts?.total ?? '—'} to="/products" />
        <Stat label="Not yet classified" value={counts?.unclassified ?? '—'} to="/products" />
      </div>
    </Panel>
  )
}

/** Admin: real platform stats already exposed by GET /admin/stats but
 * never shown anywhere before this - user counts by role, case volume. */
function AdminGlance() {
  const [stats, setStats] = useState<{ users: number; openCases: number; closedCases: number } | null>(
    null,
  )

  useEffect(() => {
    let cancelled = false
    adminApi
      .stats()
      .then((s) => {
        if (cancelled) return
        setStats({
          users: Object.values(s.users_by_role).reduce((a, b) => a + b, 0),
          openCases: s.open_cases,
          closedCases: s.closed_cases,
        })
      })
      .catch(() => {
        if (!cancelled) setStats({ users: 0, openCases: 0, closedCases: 0 })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Panel title="Platform at a glance">
      <div className="grid grid-cols-3 gap-4">
        <Stat label="Users" value={stats?.users ?? '—'} to="/admin" />
        <Stat label="Open cases" value={stats?.openCases ?? '—'} to="/cases" />
        <Stat label="Closed cases" value={stats?.closedCases ?? '—'} to="/cases" />
      </div>
    </Panel>
  )
}

/** Role-appropriate real-data summary for the dashboard's "what needs
 * attention" slot (brief: facilitator/expert/admin workspaces should
 * optimize for this). Every number here comes from an endpoint the app
 * already calls elsewhere - no new backend work, no fabricated metrics. */
export function DashboardAtAGlance({ role }: { role: UserRole }) {
  if (role === 'facilitator' || role === 'regulatory_expert') return <CaseQueueGlance />
  if (role === 'admin') return <AdminGlance />
  return <ProductsGlance />
}
