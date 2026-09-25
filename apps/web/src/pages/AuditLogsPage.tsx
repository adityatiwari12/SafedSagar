import { useEffect, useState } from 'react'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import { adminApi, AuditLogEntryOut } from '../api/adminApi'
import { ApiError } from '../api/http'
import { EmptyState, ErrorState, LoadingState, PageHeader } from '../ui/primitives'

function summarizeDetail(detail: Record<string, unknown> | null): string {
  if (!detail) return ''
  return Object.entries(detail)
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(' · ')
}

export default function AuditLogsPage() {
  const [entries, setEntries] = useState<AuditLogEntryOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionFilter, setActionFilter] = useState('')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setEntries(await adminApi.listAuditLogs())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const actionKinds = [...new Set(entries.map((e) => e.action))].sort()
  const visible = entries.filter((e) => !actionFilter || e.action === actionFilter)

  return (
    <AppWorkspaceShell>
      <div className="space-y-5">
        <PageHeader
          title="Audit Logs"
          description="Every recorded system action — the real, immutable trail every write in this app already produces."
        />

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setActionFilter('')}
            className={`gov-btn-secondary !py-1 text-xs ${actionFilter === '' ? 'border-primary bg-primary/10' : ''}`}
          >
            All actions
          </button>
          {actionKinds.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => setActionFilter(a)}
              className={`gov-btn-secondary !py-1 text-xs ${actionFilter === a ? 'border-primary bg-primary/10' : ''}`}
            >
              {a}
            </button>
          ))}
          <button type="button" onClick={() => void load()} className="gov-btn-secondary !py-1 text-xs">
            Refresh
          </button>
        </div>

        {error && (
          <div>
            <ErrorState message={error} />
            <button type="button" className="gov-btn-secondary mt-2 !py-1 text-xs" onClick={() => void load()}>
              Retry
            </button>
          </div>
        )}

        {loading && <LoadingState label="Loading audit logs…" />}

        {!loading && !error && visible.length === 0 && (
          <EmptyState
            title="No audit entries in this view"
            description="Actions across the platform (report generation, role changes, ABS saves, document uploads...) are recorded here as they happen."
          />
        )}

        {!loading && !error && visible.length > 0 && (
          <div className="overflow-x-auto border border-surface-border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-ivory/80 text-[11px] uppercase tracking-wide text-ink-faint">
                <tr>
                  <th className="px-4 py-2">When</th>
                  <th className="px-4 py-2">Actor</th>
                  <th className="px-4 py-2">Action</th>
                  <th className="px-4 py-2">Detail</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((e) => (
                  <tr key={e.id} className="border-b border-line/60 align-top">
                    <td className="py-2 pr-4 whitespace-nowrap text-ink-muted">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 text-ink">{e.actor_email ?? '—'}</td>
                    <td className="py-2 pr-4 font-semibold text-navy">{e.action}</td>
                    <td className="py-2 pr-4 text-ink-muted">{summarizeDetail(e.detail)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppWorkspaceShell>
  )
}
