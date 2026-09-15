import { Link } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'
import { useAuth } from '../auth/AuthContext'

export default function RolePlaceholderPage() {
  const { user } = useAuth()

  return (
    <AppShell>
      <div className="gov-panel max-w-2xl p-6">
        <h1 className="text-2xl font-bold text-navy">Facilitator / Admin workspace</h1>
        <p className="mt-2 text-ink-muted">
          Escalation queue and corpus administration for facilitator and admin roles will be
          available here. Your account role
          {user ? (
            <>
              {' '}
              (<strong>{user.role}</strong>)
            </>
          ) : null}{' '}
          does not use the citizen-facing Sahayak desk.
        </p>
        <Link to="/login" className="gov-btn-secondary mt-4 inline-flex">
          Back to login
        </Link>
      </div>
    </AppShell>
  )
}
