import { useState } from 'react'

// For someone who doesn't know how to phrase their question at all. Asks
// three short, concrete questions and composes them into one well-formed
// opening message - the existing pipeline (clarifying questions if still
// unclear, classification, citations, action plan) takes it from there
// and drives the rest of the 8-step journey (JourneyStepper) exactly as
// it would for a freely-typed question. This isn't a separate intake
// pipeline - it's a friendlier way to produce the first message.

const USE_OPTIONS = [
  'a drug/medicine',
  'a food or dietary product (Ayurveda Aahara)',
  'a cosmetic',
  'not sure yet - still researching',
]

const GOAL_OPTIONS = [
  'Can I patent or protect it?',
  'What approvals or licenses do I need?',
  'Is there a biodiversity/ABS angle I should know about?',
  "I'm not sure - just want general guidance",
]

export function GuidedIntakeForm({
  onComplete,
  onCancel,
}: {
  onComplete: (composedText: string) => void
  onCancel: () => void
}) {
  const [step, setStep] = useState(0)
  const [what, setWhat] = useState('')
  const [use, setUse] = useState('')

  return (
    <div className="rounded-sm border border-dashed border-surface-border bg-surface-muted/60 p-4 text-sm">
      <div className="mb-3 flex items-center justify-between">
        <p className="font-semibold text-navy">Let's walk through it - step {step + 1} of 3</p>
        <button type="button" className="text-xs text-ink-faint underline" onClick={onCancel}>
          Cancel
        </button>
      </div>

      {step === 0 && (
        <div className="space-y-2">
          <label htmlFor="guided-what" className="block font-medium text-ink">
            What have you made, or what are you researching?
          </label>
          <textarea
            id="guided-what"
            className="gov-input min-h-[3rem] w-full"
            placeholder="e.g. a formulation combining Ashwagandha and Brahmi for memory support"
            value={what}
            onChange={(e) => setWhat(e.target.value)}
            autoFocus
          />
          <button
            type="button"
            className="gov-btn-primary !py-1.5"
            disabled={!what.trim()}
            onClick={() => setStep(1)}
          >
            Next
          </button>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-2">
          <p className="font-medium text-ink">What's it mainly for?</p>
          <div className="space-y-1">
            {USE_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => {
                  setUse(option)
                  setStep(2)
                }}
                className="block w-full rounded-sm border border-surface-border bg-white px-3 py-2 text-left hover:border-primary hover:bg-blue-50"
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-2">
          <p className="font-medium text-ink">What are you hoping to find out?</p>
          <div className="space-y-1">
            {GOAL_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() =>
                  onComplete(
                    [
                      `I have made or am researching: ${what.trim()}.`,
                      `It's mainly ${use}.`,
                      `What I want to know: ${option}`,
                    ].join(' '),
                  )
                }
                className="block w-full rounded-sm border border-surface-border bg-white px-3 py-2 text-left hover:border-primary hover:bg-blue-50"
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
