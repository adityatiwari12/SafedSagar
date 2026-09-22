import { ReactNode, useState } from 'react'
import { ChatTurnResponse, RelatedProvision } from '../api/chatApi'
import { useLanguage } from '../i18n/LanguageContext'
import { CitationList } from './CitationList'
import { ConfidenceBadge, StatusBadge } from '../ui/primitives'

const RELATED_PROVISIONS_VISIBLE = 5

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
    <section className={`border-t ${border} pt-4 first:border-t-0 first:pt-0`}>
      <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {title}
      </h3>
      {children}
    </section>
  )
}

/** Small uppercase-label + content block, for grouping fields inside a cluster via spacing rather than borders. */
function MetaField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">{label}</p>
      {children}
    </div>
  )
}

// Backend `via` strings look like "Traditional knowledge --RELATES_TO--> The
// Patents Act, 1970 - Section 3 [curated; source: ipindia-patents-act-1970
// 3]" - readable but built for provenance, not prose. Strip the trailing
// provenance bracket and swap the --RELATION--> marker for a plain arrow so
// it reads as a sentence in the UI.
function formatVia(via: string): string {
  return via
    .replace(/--[A-Z_]+-->/g, ' → ')
    .replace(/\s*\[[^\]]*\]\s*$/, '')
    .trim()
}

function RelatedProvisionRow({ item }: { item: RelatedProvision }) {
  const { t } = useLanguage()
  const jurisdictionLabel =
    item.jurisdiction === 'india' ? t('jurisdiction.india') : t('jurisdiction.international')
  return (
    <li className="border-l-2 border-dashed border-line bg-surface-muted/40 px-3 py-2.5">
      <p className="text-sm font-semibold text-ink">
        {item.title}
        {item.section_or_article && (
          <span className="font-normal text-ink-muted"> · {item.section_or_article}</span>
        )}
      </p>
      <div className="mt-1">
        <StatusBadge status="draft" label={jurisdictionLabel} />
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
        {t('chat.connectedThrough')}: {formatVia(item.via)}
      </p>
      {item.source_url && (
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1.5 inline-block text-xs font-semibold text-forest underline-offset-2 hover:underline"
        >
          {t('chat.relatedSourceLink')}
        </a>
      )}
    </li>
  )
}

function RelatedProvisionsBlock({ items }: { items: RelatedProvision[] }) {
  const { t } = useLanguage()
  const [expanded, setExpanded] = useState(false)
  if (items.length === 0) return null

  const visible = expanded ? items : items.slice(0, RELATED_PROVISIONS_VISIBLE)
  const hiddenCount = items.length - visible.length

  return (
    <div className="mt-4 border-t border-surface-border pt-4">
      <h4 className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {t('chat.sectionRelatedProvisions')}
      </h4>
      <p className="mt-1 text-xs text-ink-faint">{t('chat.relatedProvisionsHint')}</p>
      <ul className="mt-2.5 space-y-2">
        {visible.map((item, i) => (
          <RelatedProvisionRow key={`${item.doc_id}-${item.section_or_article ?? ''}-${i}`} item={item} />
        ))}
      </ul>
      {hiddenCount > 0 && (
        <button
          type="button"
          className="mt-2 text-xs font-semibold text-forest underline decoration-dotted underline-offset-2"
          onClick={() => setExpanded(true)}
        >
          {t('chat.relatedProvisionsMore').replace('{count}', String(hiddenCount))}
        </button>
      )}
      {expanded && items.length > RELATED_PROVISIONS_VISIBLE && (
        <button
          type="button"
          className="mt-2 ml-3 text-xs font-semibold text-forest underline decoration-dotted underline-offset-2"
          onClick={() => setExpanded(false)}
        >
          {t('chat.relatedProvisionsShowLess')}
        </button>
      )}
    </div>
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
  const showAttention = absActive || showLimitations
  const relatedProvisions = response.related_provisions ?? []
  const answeredBy = response.answered_by

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
    <div className="space-y-5 rounded-sm border border-surface-border bg-white p-4 sm:p-6">
      {/* Answer cluster - the focal point of the panel: larger type, generous
          leading, a bounded line length, with routing rationale tucked
          underneath as quiet supporting text rather than a competing section. */}
      <Section title={t('chat.sectionAnswer')}>
        {response.used_conversation_context && (
          <p className="mb-2.5 flex items-center gap-1.5 text-xs font-medium text-ink-faint">
            <span aria-hidden="true">↳</span>
            {t('chat.consideredContext')}
          </p>
        )}
        {response.answer && (
          <div
            className="max-w-[70ch] whitespace-pre-wrap text-base leading-[1.7] text-ink sm:text-[1.05rem]"
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
        {whyBits.length > 0 && (
          <div className="mt-4">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
              {t('chat.sectionWhy')}
            </p>
            <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-relaxed text-ink-muted">
              {whyBits.map((bit) => (
                <li key={bit}>{bit}</li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      {/* Assessment cluster - classification, jurisdiction, confidence and
          model provenance grouped as supporting metadata, one shared spacing
          rhythm instead of four equal-weight sections. */}
      <Section title={t('chat.sectionAssessment')}>
        <div className="grid gap-4 sm:grid-cols-3">
          <MetaField label={t('chat.sectionClassification')}>
            <div className="flex flex-wrap gap-1.5">
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
          </MetaField>
          <MetaField label={t('chat.sectionJurisdiction')}>
            <p className="text-sm text-ink">
              <span className="font-semibold text-navy">{jurisdictionLabel}</span>
            </p>
            <p className="mt-0.5 text-xs text-ink-muted">{t('chat.jurisdictionNote')}</p>
          </MetaField>
          <MetaField label={t('chat.sectionConfidence')}>
            <ConfidenceBadge band={response.confidence_band} confidence={response.confidence} />
          </MetaField>
        </div>
        {answeredBy && (
          <p className="mt-3 border-t border-dashed border-surface-border pt-2.5 text-xs text-ink-faint">
            {t('chat.answeredBy')
              .replace('{provider}', answeredBy.provider)
              .replace('{model}', answeredBy.model)}
            {answeredBy.fallback_used && (
              <span className="ml-1.5 font-semibold text-amber-800">
                {t('chat.answeredByFallback')}
              </span>
            )}
          </p>
        )}
      </Section>

      {/* Evidence cluster - what the answer actually cited, then adjacent
          knowledge-graph context. Visually distinct treatments (solid
          saffron-edged cards vs. dashed neutral rows) so the two are never
          mistaken for each other. */}
      <Section title={t('chat.sectionEvidence')}>
        {response.citations.length > 0 ? (
          <CitationList citations={response.citations} />
        ) : (
          <p className="text-sm text-ink-muted">{t('chat.noEvidence')}</p>
        )}
        <RelatedProvisionsBlock items={relatedProvisions} />
      </Section>

      {/* Attention cluster - things the user needs to notice before acting:
          ABS/TK flags, limitations, escalation. Grouped under one heading so
          they read as one set of caveats rather than three separate alerts. */}
      {showAttention && (
        <Section title={t('chat.sectionAttention')} tone="warn">
          <div className="space-y-4">
            {absActive && abs && (
              <aside
                className="border border-saffron/50 bg-orange-50 px-3 py-2.5 text-sm text-ink"
                aria-label="ABS and traditional knowledge check"
              >
                <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                  {t('chat.sectionAbs')}
                </p>
                <ul className="list-disc space-y-1 pl-4">
                  {abs.biological_resource_likely && <li>{t('chat.absBio')}</li>}
                  {abs.traditional_knowledge_likely && <li>{t('chat.absTk')}</li>}
                </ul>
                {abs.note && <p className="mt-2 text-ink-muted">{abs.note}</p>}
              </aside>
            )}

            {showLimitations && (
              <div>
                <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                  {t('chat.sectionLimitations')}
                </p>
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
              </div>
            )}

            {response.escalate_recommended && (
              <div>
                <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
                  {t('chat.sectionEscalation')}
                </p>
                <p className="text-sm text-red-900">{t('chat.escalationHint')}</p>
              </div>
            )}
          </div>
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
    </div>
  )
}
