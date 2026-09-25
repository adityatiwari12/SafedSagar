import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { casesApi } from '../api/casesApi'

/** Real, not decorative: shows the caller's own open case-queue count
 * (the same data /cases itself lists), for the two roles that actually
 * have a queue (see app/cases/router.py's _ROLE_QUEUE - facilitator and
 * regulatory_expert only; admin/user roles get an empty list there, so
 * there is nothing honest to show them yet). No new backend endpoint -
 * this is the brief's "notifications" slot filled with real data instead
 * of a fabricated counter. */
export function NotificationBell({ role }: { role: string }) {
  const navigate = useNavigate()
  const [count, setCount] = useState<number | null>(null)

  const relevant = role === 'facilitator' || role === 'regulatory_expert'

  useEffect(() => {
    if (!relevant) return
    let cancelled = false
    casesApi
      .list('open')
      .then((cases) => {
        if (!cancelled) setCount(cases.length)
      })
      .catch(() => {
        if (!cancelled) setCount(null)
      })
    return () => {
      cancelled = true
    }
  }, [relevant])

  if (!relevant) return null

  return (
    <button
      type="button"
      onClick={() => navigate('/cases')}
      className="relative flex h-8 w-8 shrink-0 items-center justify-center border border-surface-border bg-white text-ink-faint hover:border-saffron hover:text-saffron-deep"
      aria-label={count ? `${count} open cases awaiting you` : 'Open cases'}
      title="Open case queue"
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
        <path
          d="M12 4a6 6 0 0 0-6 6v3.5L4.5 16h15L18 13.5V10a6 6 0 0 0-6-6Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {count !== null && count > 0 && (
        <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-[1rem] items-center justify-center border border-white bg-saffron px-0.5 text-[9px] font-bold text-white">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  )
}
