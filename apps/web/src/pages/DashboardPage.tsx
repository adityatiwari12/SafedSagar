import { Link } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { PageHeader, Panel, StatusBadge } from '../ui/primitives'
import { useAuth } from '../auth/AuthContext'
import { navForRole } from '../layout/navConfig'
import { DashboardAtAGlance } from './DashboardAtAGlance'

export default function DashboardPage() {
  const { user } = useAuth()
  if (!user) return null

  const ready = navForRole(user.role, user.persona).filter((n) => n.ready && n.to !== '/dashboard')
  const roleLabel = user.role.replace(/_/g, ' ')

  const blurb =
    user.role === 'admin'
      ? 'Monitor users, cases and platform health. Expand Knowledge Base and AI Quality modules as they come online.'
      : user.role === 'facilitator'
        ? 'Triage the case queue, claim work, and escalate low-confidence AI assessments to experts.'
        : user.role === 'regulatory_expert'
          ? 'Validate assigned cases against evidence, correct AI conclusions, and request missing information.'
          : user.persona === 'practitioner_researcher'
            ? 'Research Sahayak, projects and prior-art workflows — always citation-grounded.'
            : user.persona === 'cultivator'
              ? 'Track biological resources, TK/ABS indicators and documentation for what you cultivate.'
              : 'Ask IP-SAKTI, manage product dossiers, and escalate when confidence is insufficient.'

  return (
    <AppWorkspaceShell>
      <PageHeader
        title="Dashboard"
        description={`Signed in as ${roleLabel}. ${blurb}`}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Your workspace" className="lg:col-span-2">
          <ul className="grid gap-2 sm:grid-cols-2">
            {ready.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.to}
                  className="flex items-center justify-between border border-surface-border px-3 py-3 text-sm font-semibold text-navy transition-colors hover:border-forest hover:bg-ivory"
                >
                  {item.label}
                  <span className="text-ink-faint" aria-hidden="true">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Panel>

        <div className="space-y-4">
          <DashboardAtAGlance role={user.role} persona={user.persona} />
          <Panel title="Operating principles">
            <ul className="space-y-3 text-sm text-ink-muted">
              <li className="flex gap-2">
                <StatusBadge status="high" label="Evidence" />
                <span>Claims must cite retrieved sources.</span>
              </li>
              <li className="flex gap-2">
                <StatusBadge status="medium" label="Jurisdiction" />
                <span>India and International stay on separate tracks.</span>
              </li>
              <li className="flex gap-2">
                <StatusBadge status="low" label="Human review" />
                <span>Escalate when confidence is insufficient.</span>
              </li>
            </ul>
            <p className="mt-4 text-xs text-ink-faint">
              Guidance is informational — confirm filings against official gazettes.
            </p>
          </Panel>
        </div>
      </div>
    </AppWorkspaceShell>
  )
}
