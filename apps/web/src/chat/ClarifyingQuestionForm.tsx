import { FormEvent, useState } from 'react'

export function ClarifyingQuestionForm({
  questions,
  onSubmit,
  disabled,
}: {
  questions: string[]
  onSubmit: (answers: Record<string, string>) => void
  disabled?: boolean
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({})

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const filled = Object.fromEntries(
      questions.map((q) => [q, (answers[q] ?? '').trim()]).filter(([, v]) => v),
    )
    if (Object.keys(filled).length === 0) return
    onSubmit(filled)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="gov-panel border-l-4 border-saffron p-4"
      aria-labelledby="clarify-heading"
    >
      <h3 id="clarify-heading" className="text-base font-bold text-navy">
        Minimum clarifying questions
      </h3>
      <p className="mt-1 text-sm text-ink-muted">
        Answer what you can — this helps classify the product and route the right law set.
      </p>
      <div className="mt-4 space-y-4">
        {questions.map((q, i) => (
          <div key={q}>
            <label className="gov-label" htmlFor={`clarify-${i}`}>
              {q}
            </label>
            <input
              id={`clarify-${i}`}
              className="gov-input"
              value={answers[q] ?? ''}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [q]: e.target.value }))}
              disabled={disabled}
            />
          </div>
        ))}
      </div>
      <button type="submit" className="gov-btn-primary mt-4" disabled={disabled}>
        Continue analysis
      </button>
    </form>
  )
}
