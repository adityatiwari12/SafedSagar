import { useState } from 'react'

export function EscalateButton({
  emphasized,
  onEscalate,
  disabled,
}: {
  emphasized?: boolean
  onEscalate: () => Promise<{ escalation_id: string } | null>
  disabled?: boolean
}) {
  const [result, setResult] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleClick() {
    setBusy(true)
    try {
      const res = await onEscalate()
      if (res) setResult(`Escalation queued: ${res.escalation_id}`)
      else setResult('Start a conversation first, then escalate.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className={`gov-panel p-4 ${emphasized ? 'border-l-4 border-red-700 bg-red-50' : ''}`}
    >
      <h3 className="text-base font-bold text-navy">Need a human IP facilitator?</h3>
      <p className="mt-1 text-sm text-ink-muted">
        {emphasized
          ? 'This answer has low confidence or may need expert review. Escalation is recommended.'
          : 'You can escalate any time. Facilitators pick up items from the Phase 6 queue.'}
      </p>
      <button
        type="button"
        className={`mt-3 ${emphasized ? 'gov-btn-danger' : 'gov-btn-secondary'}`}
        onClick={handleClick}
        disabled={disabled || busy}
      >
        {busy ? 'Submitting…' : 'Talk to a human IP facilitator'}
      </button>
      {result && (
        <p className="mt-2 text-sm font-medium text-indiaGreen" role="status">
          {result}
        </p>
      )}
    </div>
  )
}
