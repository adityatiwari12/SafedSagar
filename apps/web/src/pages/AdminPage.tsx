import { useEffect, useState } from 'react'
import { AppShell } from '../layout/AppShell'
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
    <AppShell>
      <div className="space-y-5">
        <header>
          <h1 className="text-2xl font-bold text-navy">Platform administration</h1>
          <p className="mt-1 text-sm text-ink-muted">Users, roles, and escalation activity.</p>
        </header>

        {error && (
          <p className="rounded-sm bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
            {error}
          </p>
        )}

        {loading && <p className="text-sm text-ink-muted">Loading…</p>}

        {stats && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Object.entries(stats.users_by_role).map(([role, count]) => (
              <div key={role} className="gov-panel p-3 text-center">
                <p className="text-2xl font-bold text-navy">{count}</p>
                <p className="text-xs uppercase tracking-wide text-ink-muted">{role.replace('_', ' ')}</p>
              </div>
            ))}
            <div className="gov-panel p-3 text-center">
              <p className="text-2xl font-bold text-red-700">{stats.open_cases}</p>
              <p className="text-xs uppercase tracking-wide text-ink-muted">open cases</p>
            </div>
            <div className="gov-panel p-3 text-center">
              <p className="text-2xl font-bold text-green-700">{stats.closed_cases}</p>
              <p className="text-xs uppercase tracking-wide text-ink-muted">closed cases</p>
            </div>
          </div>
        )}

        <div className="gov-panel overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-muted text-xs uppercase tracking-wide text-ink-faint">
              <tr>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Persona</th>
                <th className="px-3 py-2">Verification</th>
                <th className="px-3 py-2">Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-line">
                  <td className="px-3 py-2">{u.email}</td>
                  <td className="px-3 py-2 capitalize">{u.role.replace('_', ' ')}</td>
                  <td className="px-3 py-2 text-ink-muted">{u.persona ?? '—'}</td>
                  <td className="px-3 py-2 capitalize">{u.verification_status}</td>
                  <td className="px-3 py-2 text-ink-muted">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  )
}
