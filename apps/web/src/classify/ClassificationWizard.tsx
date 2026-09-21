import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppWorkspaceShell } from '../layout/AppWorkspaceShell'
import {
  Basis,
  ClassificationResult,
  EvidenceBasis,
  IntendedUse,
  classify,
  describeAnswersForChat,
} from './decisionTree'

type Step = 'describe' | 'basis' | 'use' | 'evidence' | 'result'

const CATEGORY_LABELS: Record<ClassificationResult['category'], string> = {
  classical_or_generic_medicine: 'Classical / generic medicine',
  patent_or_proprietary_medicine: 'Patent / proprietary medicine',
  new_or_non_classical_drug: 'New / non-classical drug',
  phytopharmaceutical: 'Phytopharmaceutical',
  ayurveda_aahara_or_nutraceutical: 'Ayurveda-Aahara / nutraceutical',
  cosmetic: 'Cosmetic',
  unclear: 'Unclear',
}

const CONFIDENCE_STYLES: Record<ClassificationResult['confidence'], string> = {
  high: 'bg-green-100 text-green-900 border-green-700',
  medium: 'bg-amber-100 text-amber-950 border-amber-700',
  low: 'bg-red-50 text-red-900 border-red-700',
}

function OptionButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-sm border px-4 py-3 text-left text-sm transition-colors ${
        selected
          ? 'border-primary bg-primary/10 font-semibold text-navy'
          : 'border-surface-border bg-white text-ink hover:border-primary hover:bg-blue-50'
      }`}
    >
      {children}
    </button>
  )
}

function StepDots({ step }: { step: Step }) {
  const order: Step[] = ['describe', 'basis', 'use', 'evidence', 'result']
  const index = order.indexOf(step)
  return (
    <div className="flex items-center gap-1.5" aria-hidden="true">
      {order.map((s, i) => (
        <span
          key={s}
          className={`h-1.5 flex-1 rounded-full ${i <= index ? 'bg-primary' : 'bg-surface-border'}`}
        />
      ))}
    </div>
  )
}

export default function ClassificationWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('describe')
  const [description, setDescription] = useState('')
  const [basis, setBasis] = useState<Basis | null>(null)
  const [intendedUse, setIntendedUse] = useState<IntendedUse | null>(null)
  const [evidenceBasis, setEvidenceBasis] = useState<EvidenceBasis | null>(null)

  function goToUseStep() {
    if (!basis) return
    setStep('use')
  }

  function goToNextAfterUse() {
    if (!intendedUse) return
    setStep(intendedUse === 'therapeutic' ? 'evidence' : 'result')
  }

  function goToResult() {
    if (!evidenceBasis) return
    setStep('result')
  }

  const result: ClassificationResult | null =
    step === 'result' && intendedUse
      ? classify({ basis: basis ?? 'not_sure', intendedUse, evidenceBasis: evidenceBasis ?? undefined })
      : null

  function continueToChat() {
    if (!result) return
    const seeded = describeAnswersForChat(description, result)
    navigate('/ask', { state: { seededDraft: seeded } })
  }

  function restart() {
    setStep('describe')
    setBasis(null)
    setIntendedUse(null)
    setEvidenceBasis(null)
  }

  return (
    <AppWorkspaceShell>
      <div className="mx-auto max-w-2xl space-y-5">
        <header>
          <h1 className="text-2xl font-bold text-navy">Product classification</h1>
          <p className="mt-1 text-sm text-ink-muted">
            A few questions decide which of the six product categories applies — this changes the
            IP and regulatory pathway entirely, so it comes before any IP/ABS guidance.
          </p>
        </header>

        <StepDots step={step} />

        <div className="gov-panel space-y-4 p-5">
          {step === 'describe' && (
            <div className="space-y-3">
              <label className="gov-label" htmlFor="description">
                Briefly describe the product or innovation
              </label>
              <textarea
                id="description"
                className="gov-input min-h-[5rem]"
                placeholder="e.g. A herbal formulation using Ashwagandha and Brahmi for stress management…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
              <button
                type="button"
                className="gov-btn-primary"
                disabled={!description.trim()}
                onClick={() => setStep('basis')}
              >
                Continue
              </button>
            </div>
          )}

          {step === 'basis' && (
            <div className="space-y-3">
              <p className="gov-label">
                Is the formulation drawn from an authoritative classical Ayurvedic text, or is it
                a new / proprietary composition?
              </p>
              <div className="space-y-2">
                <OptionButton selected={basis === 'classical'} onClick={() => setBasis('classical')}>
                  Classical text-based — same formulation and method as a First-Schedule text
                </OptionButton>
                <OptionButton
                  selected={basis === 'new_or_proprietary'}
                  onClick={() => setBasis('new_or_proprietary')}
                >
                  New or proprietary — a novel combination, process, or dosage, even if using known
                  ingredients
                </OptionButton>
                <OptionButton selected={basis === 'not_sure'} onClick={() => setBasis('not_sure')}>
                  Not sure
                </OptionButton>
              </div>
              <div className="flex gap-2">
                <button type="button" className="gov-btn-secondary" onClick={() => setStep('describe')}>
                  Back
                </button>
                <button type="button" className="gov-btn-primary" disabled={!basis} onClick={goToUseStep}>
                  Continue
                </button>
              </div>
            </div>
          )}

          {step === 'use' && (
            <div className="space-y-3">
              <p className="gov-label">What is the primary intended use?</p>
              <div className="space-y-2">
                <OptionButton
                  selected={intendedUse === 'therapeutic'}
                  onClick={() => setIntendedUse('therapeutic')}
                >
                  Therapeutic / medicinal — treats or manages a health condition
                </OptionButton>
                <OptionButton selected={intendedUse === 'food'} onClick={() => setIntendedUse('food')}>
                  Food / nutraceutical (Ayurveda Aahara) — no disease-treatment claim
                </OptionButton>
                <OptionButton
                  selected={intendedUse === 'cosmetic'}
                  onClick={() => setIntendedUse('cosmetic')}
                >
                  Cosmetic — external use, appearance-related
                </OptionButton>
              </div>
              <div className="flex gap-2">
                <button type="button" className="gov-btn-secondary" onClick={() => setStep('basis')}>
                  Back
                </button>
                <button
                  type="button"
                  className="gov-btn-primary"
                  disabled={!intendedUse}
                  onClick={goToNextAfterUse}
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {step === 'evidence' && (
            <div className="space-y-3">
              <p className="gov-label">
                Does this formulation already have established safety/effectiveness from classical
                use, or does it need new scientific evidence?
              </p>
              <div className="space-y-2">
                <OptionButton
                  selected={evidenceBasis === 'established_classical'}
                  onClick={() => setEvidenceBasis('established_classical')}
                >
                  Relies on established / classical use — no new clinical evidence generated
                </OptionButton>
                <OptionButton
                  selected={evidenceBasis === 'new_evidence_needed'}
                  onClick={() => setEvidenceBasis('new_evidence_needed')}
                >
                  Requires new safety/effectiveness evidence — a genuinely new drug
                </OptionButton>
                <OptionButton
                  selected={evidenceBasis === 'phytopharmaceutical'}
                  onClick={() => setEvidenceBasis('phytopharmaceutical')}
                >
                  Standardized plant-extract-based drug with a defined pharmacological action
                </OptionButton>
                <OptionButton
                  selected={evidenceBasis === 'not_sure'}
                  onClick={() => setEvidenceBasis('not_sure')}
                >
                  Not sure
                </OptionButton>
              </div>
              <div className="flex gap-2">
                <button type="button" className="gov-btn-secondary" onClick={() => setStep('use')}>
                  Back
                </button>
                <button
                  type="button"
                  className="gov-btn-primary"
                  disabled={!evidenceBasis}
                  onClick={goToResult}
                >
                  See classification
                </button>
              </div>
            </div>
          )}

          {step === 'result' && result && (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                  Classification
                </p>
                <h2 className="mt-1 text-xl font-bold text-navy">
                  {CATEGORY_LABELS[result.category]}
                </h2>
              </div>

              <span
                className={`inline-flex items-center rounded-sm border px-2.5 py-1 text-xs font-bold uppercase tracking-wide ${CONFIDENCE_STYLES[result.confidence]}`}
              >
                Confidence: {result.confidence}
              </span>

              <p className="text-sm text-ink-muted">{result.rationale}</p>

              <div className="rounded-sm border-l-4 border-indiaGreen bg-surface-muted/60 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                  What this means
                </p>
                <p className="mt-1 text-sm text-ink">{result.implication}</p>
              </div>

              <div className="flex flex-wrap gap-2 border-t border-line pt-3">
                <button type="button" className="gov-btn-primary" onClick={continueToChat}>
                  Continue to Ask Sahayak
                </button>
                <button type="button" className="gov-btn-secondary" onClick={restart}>
                  Start over
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppWorkspaceShell>
  )
}
