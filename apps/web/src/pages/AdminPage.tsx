import { useEffect, useState } from 'react'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel, StatusBadge } from '../ui/primitives'
import { adminApi, AdminStats, AdminUserSummary } from '../api/adminApi'
import { ApiError } from '../api/http'

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUserSummary[]>([])
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [userList, statsData] = await Promise.all([adminApi.listUsers(), adminApi.stats()])
        setUsers(userList)
        setStats(statsData)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Failed to load admin data')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return (
    <AppWorkspaceShell>
      <PageHeader
        title="Platform administration"
        description="Users, roles, and escalation activity. Knowledge Base and AI Quality modules come online next."
      />
      <div className="space-y-5">
        {error && <ErrorState message={error} />}
        {loading && <LoadingState />}

        {stats && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Object.entries(stats.users_by_role).map(([role, count]) => (
              <Panel key={role}>
                <div className="text-center">
                  <p className="text-2xl font-bold text-navy">{count}</p>
                  <p className="text-[11px] uppercase tracking-wide text-ink-muted">
                    {role.replace('_', ' ')}
                  </p>
                </div>
              </Panel>
            ))}
            <Panel>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-700">{stats.open_cases}</p>
                <p className="text-[11px] uppercase tracking-wide text-ink-muted">open cases</p>
              </div>
            </Panel>
            <Panel>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-700">{stats.closed_cases}</p>
                <p className="text-[11px] uppercase tracking-wide text-ink-muted">closed cases</p>
              </div>
            </Panel>
          </div>
        )}

        <Panel title="Users">
          {users.length === 0 && !loading ? (
            <EmptyState title="No users yet" />
          ) : (
            <div className="-m-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-ivory/80 text-[11px] uppercase tracking-wide text-ink-faint">
                  <tr>
                    <th className="px-4 py-2">Email</th>
                    <th className="px-4 py-2">Role</th>
                    <th className="px-4 py-2">Persona</th>
                    <th className="px-4 py-2">Verification</th>
                    <th className="px-4 py-2">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-t border-line">
                      <td className="px-4 py-2">{u.email}</td>
                      <td className="px-4 py-2">
                        <StatusBadge status="medium" label={u.role.replace(/_/g, ' ')} />
                      </td>
                      <td className="px-4 py-2 text-ink-muted">{u.persona ?? '—'}</td>
                      <td className="px-4 py-2">
                        <StatusBadge
                          status={u.verification_status === 'approved' ? 'resolved' : 'draft'}
                          label={u.verification_status}
                        />
                      </td>
                      <td className="px-4 py-2 text-ink-muted">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </AppWorkspaceShell>
  )
}
