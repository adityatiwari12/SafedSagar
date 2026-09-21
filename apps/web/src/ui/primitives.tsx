/** Shared UI primitives for the authenticated IP-SAKTI workspace. */

import { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
}: {
  title: string
  description?: string
  actions?: ReactNode
  breadcrumb?: ReactNode
}) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-surface-border pb-4">
      <div className="min-w-0">
        {breadcrumb && <div className="mb-1 text-xs text-ink-faint">{breadcrumb}</div>}
        <h1 className="text-xl font-extrabold tracking-tight text-navy sm:text-2xl">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-start justify-center border border-dashed border-surface-border bg-ivory/60 px-6 py-10">
      <p className="text-base font-bold text-forest">{title}</p>
      {description && <p className="mt-2 max-w-lg text-sm text-ink-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <p className="text-sm text-ink-muted" role="status">
      {label}
    </p>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p className="rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900" role="alert">
      {message}
    </p>
  )
}

const BADGE =
  'inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide'

const STATUS: Record<string, string> = {
  open: 'bg-red-50 text-red-900 border-red-700',
  in_progress: 'bg-amber-100 text-amber-950 border-amber-700',
  awaiting_user_input: 'bg-amber-100 text-amber-950 border-amber-700',
  escalated: 'bg-red-50 text-red-900 border-red-700',
  resolved: 'bg-green-100 text-green-900 border-green-700',
  closed: 'bg-green-100 text-green-900 border-green-700',
  draft: 'bg-surface-muted text-ink-muted border-line',
  high: 'bg-green-100 text-green-900 border-green-700',
  medium: 'bg-amber-100 text-amber-950 border-amber-700',
  low: 'bg-red-50 text-red-900 border-red-700',
  insufficient: 'bg-surface-muted text-ink-muted border-line',
}

export function StatusBadge({
  status,
  label,
}: {
  status: string
  label?: string
}) {
  return (
    <span className={`${BADGE} ${STATUS[status] ?? 'bg-surface-muted text-ink-muted border-line'}`}>
      {label ?? status.replace(/_/g, ' ')}
    </span>
  )
}

export function ConfidenceBadge({
  band,
  confidence,
  reason,
}: {
  band: 'high' | 'medium' | 'low' | 'insufficient'
  confidence?: number
  reason?: string
}) {
  const pct = confidence !== undefined ? ` (${Math.round(confidence * 100)}%)` : ''
  const defaultReason =
    band === 'high'
      ? 'Strong citation coverage and consistent classification signals.'
      : band === 'medium'
        ? 'Partial evidence or mixed signals — verify against official sources.'
        : band === 'low'
          ? 'Low confidence — this answer may be incomplete. Prefer rephrasing your question or escalating to a human IP facilitator rather than relying on this alone.'
          : 'Not enough retrieved evidence to support a reliable answer.'

  return (
    <div className="space-y-1.5">
      <StatusBadge status={band === 'insufficient' ? 'insufficient' : band} label={`Confidence: ${band}${pct}`} />
      <p className="text-xs leading-relaxed text-ink-muted">{reason ?? defaultReason}</p>
    </div>
  )
}

export type EvidenceItem = {
  title: string
  authority?: string
  provision?: string
  jurisdiction?: string
  version?: string
  effectiveDate?: string
  sourceUrl?: string
  why?: string
  docId?: string
}

export function EvidenceCard({ item, index }: { item: EvidenceItem; index?: number }) {
  return (
    <article className="border-l-2 border-saffron bg-ivory/50 px-3 py-2.5">
      <p className="text-sm font-bold text-ink">
        {index !== undefined ? `[${index}] ` : ''}
        {item.title}
      </p>
      <p className="mt-1 text-xs text-ink-muted">
        {[item.authority, item.provision, item.jurisdiction, item.version].filter(Boolean).join(' · ')}
      </p>
      {(item.effectiveDate || item.docId) && (
        <p className="mt-1 text-[11px] text-ink-faint">
          {[item.docId, item.effectiveDate ? `Last verified: ${item.effectiveDate}` : null]
            .filter(Boolean)
            .join(' · ')}
        </p>
      )}
      {item.why && <p className="mt-2 text-xs leading-relaxed text-ink-muted">{item.why}</p>}
      {item.sourceUrl && (
        <a
          href={item.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-xs font-semibold text-forest underline-offset-2 hover:underline"
        >
          Official source
        </a>
      )}
    </article>
  )
}

export function EvidenceList({ items }: { items: EvidenceItem[] }) {
  if (!items.length) return null
  return (
    <ol className="space-y-3">
      {items.map((item, i) => (
        <li key={`${item.docId ?? item.title}-${i}`}>
          <EvidenceCard item={item} index={i + 1} />
        </li>
      ))}
    </ol>
  )
}

export function Panel({
  title,
  children,
  action,
  className = '',
}: {
  title?: string
  children: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <section className={`border border-surface-border bg-white ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-2 border-b border-surface-border px-4 py-2.5">
          {title ? <h2 className="text-sm font-bold text-forest">{title}</h2> : <span />}
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

export function PlannedLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link to={to} className="text-sm font-semibold text-forest underline-offset-2 hover:underline">
      {children}
    </Link>
  )
}
