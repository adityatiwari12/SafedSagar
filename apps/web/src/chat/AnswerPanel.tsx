import { ReactNode, useState } from 'react'
import { ChatTurnResponse } from '../api/chatApi'
import { useLanguage } from '../i18n/LanguageContext'
import { CitationList } from './CitationList'
import { ConfidenceBadge, StatusBadge } from '../ui/primitives'

function Section({
  title,
  children,
  tone = 'default',
}: {
  title: string
  children: ReactNode
  tone?: 'default' | 'warn' | 'accent'
}) {
  const border =
    tone === 'warn'
      ? 'border-red-200'
      : tone === 'accent'
        ? 'border-saffron/50'
        : 'border-surface-border'
  return (
    <section className={`border-t ${border} pt-3 first:border-t-0 first:pt-0`}>
      <h3 className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {title}
      </h3>
      {children}
    </section>
  )
}

export function AnswerPanel({ response }: { response: ChatTurnResponse }) {
  const { t } = useLanguage()
  const [showEnglish, setShowEnglish] = useState(false)

  if (!response.answer && response.clarifying_questions?.length) return null

  const product = response.classification.product_type.replace(/_/g, ' ')
  const ip = response.classification.ip_type.replace(/_/g, ' ')
  const jurisdictionLabel =
    response.jurisdiction === 'india' ? t('jurisdiction.india') : t('jurisdiction.international')
  const hasClassification =
    response.classification.product_type !== 'unknown' || response.classification.ip_type !== 'unknown'
  const isTranslated = Boolean(
    response.detected_language && response.detected_language !== 'en' && response.canonical_answer,
  )
  const abs = response.abs_tk_flags
  const absActive = Boolean(
    abs && (abs.biological_resource_likely || abs.traditional_knowledge_likely),
  )
  const showLimitations =
    response.confidence_band === 'low' ||
    response.needs_human_review ||
    response.escalate_recommended ||
    response.classification.product_type === 'out_of_scope' ||
    response.citations.length === 0

  const whyBits: string[] = []
  if (hasClassification) {
    whyBits.push(
      t('chat.whyClassification')
        .replace('{product}', product)
        .replace('{ip}', ip)
        .replace('{jurisdiction}', jurisdictionLabel),
    )
  }
  if (response.citations.length > 0) {
    whyBits.push(
      t('chat.whyEvidence').replace('{count}', String(response.citations.length)),
    )
  } else {
    whyBits.push(t('chat.whyNoEvidence'))
  }
  if (absActive) whyBits.push(t('chat.whyAbs'))

  return (
    <div className="space-y-3 rounded-sm border border-surface-border bg-white p-4 sm:p-5">
      <Section title={t('chat.sectionAnswer')}>
        {response.answer && (
          <div
            className="whitespace-pre-wrap text-[0.95rem] leading-relaxed text-ink"
            lang={showEnglish ? 'en' : response.detected_language || 'en'}
          >
            {showEnglish && response.canonical_answer ? response.canonical_answer : response.answer}
          </div>
        )}
        {isTranslated && (
          <button
            type="button"
            className="mt-2 text-xs font-semibold text-forest underline decoration-dotted underline-offset-2"
            onClick={() => setShowEnglish((v) => !v)}
          >
            {showEnglish ? t('chat.viewTranslated') : t('chat.viewEnglish')}
          </button>
        )}
      </Section>

      {whyBits.length > 0 && (
        <Section title={t('chat.sectionWhy')}>
          <ul className="list-disc space-y-1 pl-4 text-sm text-ink-muted">
            {whyBits.map((bit) => (
              <li key={bit}>{bit}</li>
            ))}
          </ul>
        </Section>
      )}

      <Section title={t('chat.sectionClassification')}>
        <div className="flex flex-wrap gap-2">
          <StatusBadge
            status={
              response.classification.product_type === 'out_of_scope'
                ? 'low'
                : response.classification.product_type === 'unknown'
                  ? 'draft'
                  : 'medium'
            }
            label={product}
          />
          <StatusBadge
            status={response.classification.ip_type === 'unknown' ? 'draft' : 'open'}
            label={`IP: ${ip}`}
          />
        </div>
      </Section>

      <Section title={t('chat.sectionJurisdiction')}>
        <p className="text-sm text-ink">
          <span className="font-semibold text-navy">{jurisdictionLabel}</span>
          <span className="text-ink-muted"> — {t('chat.jurisdictionNote')}</span>
        </p>
      </Section>

      <Section title={t('chat.sectionEvidence')}>
        {response.citations.length > 0 ? (
          <CitationList citations={response.citations} />
        ) : (
          <p className="text-sm text-ink-muted">{t('chat.noEvidence')}</p>
        )}
      </Section>

      <Section title={t('chat.sectionConfidence')}>
        <ConfidenceBadge band={response.confidence_band} confidence={response.confidence} />
      </Section>

      {absActive && abs && (
        <Section title={t('chat.sectionAbs')} tone="accent">
          <aside className="border border-saffron/50 bg-orange-50 px-3 py-2.5 text-sm text-ink" aria-label="ABS and traditional knowledge check">
            <ul className="list-disc space-y-1 pl-4">
              {abs.biological_resource_likely && <li>{t('chat.absBio')}</li>}
              {abs.traditional_knowledge_likely && <li>{t('chat.absTk')}</li>}
            </ul>
            {abs.note && <p className="mt-2 text-ink-muted">{abs.note}</p>}
          </aside>
        </Section>
      )}

      {showLimitations && (
        <Section title={t('chat.sectionLimitations')} tone="warn">
          <ul className="list-disc space-y-1 pl-4 text-sm text-ink-muted">
            {response.confidence_band === 'low' &&
              response.classification.product_type !== 'out_of_scope' && (
                <li>{t('chat.limitLowConfidence')}</li>
              )}
            {response.classification.product_type === 'out_of_scope' && (
              <li>{t('chat.limitOutOfScope')}</li>
            )}
            {response.citations.length === 0 && <li>{t('chat.limitNoCitations')}</li>}
            {response.needs_human_review && <li>{t('chat.limitTranslation')}</li>}
            {response.escalate_recommended && <li>{t('chat.limitEscalate')}</li>}
            <li>{t('chat.limitDisclaimer')}</li>
          </ul>
        </Section>
      )}

      {response.next_steps && response.next_steps.length > 0 && (
        <Section title={t('chat.sectionNextSteps')}>
          <ol className="list-decimal space-y-1.5 pl-4 text-sm text-ink">
            {response.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </Section>
      )}

      {response.escalate_recommended && (
        <Section title={t('chat.sectionEscalation')} tone="warn">
          <p className="text-sm text-red-900">{t('chat.escalationHint')}</p>
        </Section>
      )}
    </div>
  )
}
