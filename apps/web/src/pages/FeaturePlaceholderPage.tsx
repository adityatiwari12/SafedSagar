import { Link, useLocation } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { EmptyState, PageHeader } from '../ui/primitives'
import { navForRole } from '../layout/navConfig'
import { useAuth } from '../auth/AuthContext'

const COPY: Record<string, { title: string; body: string }> = {
  '/regulatory': {
    title: 'Regulatory',
    body: 'AYUSH, FSSAI and related pathway guidance structured by product category — separate from IP filing strategy.',
  },
  '/documents': {
    title: 'Documents',
    body: 'Product and case document library — uploads, versions and linked assessments.',
  },
  '/assessments': {
    title: 'Assessments',
    body: 'Saved AI assessments, confidence history and expert annotations.',
  },
  '/expert-assistance': {
    title: 'Expert Assistance',
    body: 'Request and track human IP facilitator or regulatory expert review.',
  },
  '/reports': {
    title: 'Reports',
    body: 'Exportable summaries for products, cases and research activity.',
  },
  '/communication': {
    title: 'Communication',
    body: 'Case messaging between users, facilitators and experts.',
  },
  '/sources': {
    title: 'Sources',
    body: 'Curated corpus browser for statutes, rules, treaties and guidance used in retrieval.',
  },
  '/organisations': {
    title: 'Organisations',
    body: 'Organisation registry and membership — API exists; management UI is next.',
  },
  '/products-admin': {
    title: 'Products (Admin)',
    body: 'Cross-tenant product oversight for platform administrators.',
  },
  '/knowledge-base': {
    title: 'Knowledge Base',
    body: 'Source registry with authority, jurisdiction, version, effective dates and supersession history.',
  },
  '/ai-quality': {
    title: 'AI Quality',
    body: 'Citation correctness, confidence distribution and escalation rates.',
  },
  '/analytics': {
    title: 'Analytics',
    body: 'National / platform activity for users, cases and languages.',
  },
  '/languages': {
    title: 'Languages',
    body: 'UI locale catalogs and IndicTrans2 translation health.',
  },
  '/jurisdictions': {
    title: 'Jurisdictions',
    body: 'India vs International routing configuration and corpus filters.',
  },
  '/audit-logs': {
    title: 'Audit Logs',
    body: 'Immutable access and mutation history for compliance review.',
  },
  '/security': {
    title: 'Security',
    body: 'Session, role and access-control posture for the platform.',
  },
}

export default function FeaturePlaceholderPage() {
  const location = useLocation()
  const { user } = useAuth()
  const path = location.pathname
  const meta = COPY[path] ?? {
    title: 'Workspace module',
    body: 'This module is part of the IP-SAKTI information architecture and will be delivered in a later slice.',
  }

  const readyLinks =
    user &&
    navForRole(user.role, user.persona)
      .filter((n) => n.ready)
      .slice(0, 4)

  return (
    <AppWorkspaceShell>
      <PageHeader
        title={meta.title}
        description="Planned workspace module — shell and navigation are live; full workflow arrives next."
      />
      <EmptyState
        title={`${meta.title} is on the roadmap`}
        description={meta.body}
        action={
          <div className="flex flex-wrap gap-3">
            {readyLinks?.map((n) => (
              <Link key={n.id} to={n.to} className="gov-btn-secondary !py-2 text-sm">
                {n.label}
              </Link>
            ))}
            <Link to="/dashboard" className="gov-btn-primary !py-2 text-sm">
              Back to Dashboard
            </Link>
          </div>
        }
      />
    </AppWorkspaceShell>
  )
}
