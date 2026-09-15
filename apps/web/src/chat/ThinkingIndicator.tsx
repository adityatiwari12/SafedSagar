import { useEffect, useState } from 'react'

// Mirrors the actual node sequence in apps/api/app/graph/graph.py - not
// decorative copy, the real pipeline stages a query passes through
// (CLAUDE.md's LangGraph-shaped node list). No backend streaming exists
// to report real progress, so this cycles on a client-side timer tuned to
// the documented ~20-25s/query latency (apps/api/.env.example) - close
// enough to feel like visible reasoning rather than a dead spinner.
const STAGES = [
  'Classifying your product…',
  'Routing jurisdiction and IP type…',
  'Retrieving authoritative sources…',
  'Reasoning through the evidence…',
  'Validating citations…',
]

const STAGE_INTERVAL_MS = 2800

export function ThinkingIndicator() {
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    const id = window.setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1))
    }, STAGE_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [])

  return (
    <p className="flex items-center gap-2 text-sm text-ink-muted" role="status">
      <span className="flex gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:0.2s]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:0.4s]" />
      </span>
      {STAGES[stageIndex]}
    </p>
  )
}
