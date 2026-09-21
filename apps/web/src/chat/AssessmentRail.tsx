import { ChatTurnResponse } from '../api/chatApi'
import { useLanguage } from '../i18n/LanguageContext'
import { ConfidenceBadge, Panel, StatusBadge } from '../ui/primitives'
import { CitationList } from './CitationList'
import { EscalateButton } from './EscalateButton'

export function AssessmentRail({
  latest,
  sending,
  onEscalate,
}: {
  latest: ChatTurnResponse | null
  sending: boolean
  onEscalate: () => Promise<{ escalation_id: string } | null>
}) {
  const { t } = useLanguage()

  if (!latest) {
    return (
      <div className="flex flex-col gap-4 pb-1">
        <Panel title={t('chat.assessmentTitle')}>
          <p className="text-sm text-ink-muted">{t('chat.assessmentEmpty')}</p>
        </Panel>
        <GuidanceCompact />
        <CorpusNote />
      </div>
    )
  }

  const product = latest.classification.product_type.replace(/_/g, ' ')
  const jurisdictionLabel =
    latest.jurisdiction === 'india' ? t('jurisdiction.india') : t('jurisdiction.international')

  return (
    <div className="flex flex-col gap-4 pb-1">
      <Panel title={t('chat.assessmentTitle')}>
        <div className="space-y-4">
          <div>
            <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
              {t('chat.sectionConfidence')}
            </p>
            <ConfidenceBadge band={latest.confidence_band} confidence={latest.confidence} />
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
              {t('chat.sectionClassification')}
            </p>
            <div className="flex flex-wrap gap-2">
              <StatusBadge status="medium" label={product} />
              <StatusBadge status="open" label={jurisdictionLabel} />
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
              {t('chat.sectionEvidence')}
            </p>
            {latest.citations.length > 0 ? (
              <CitationList citations={latest.citations.slice(0, 3)} />
            ) : (
              <p className="text-sm text-ink-muted">{t('chat.noEvidence')}</p>
            )}
            {latest.citations.length > 3 && (
              <p className="mt-2 text-xs text-ink-faint">
                {t('chat.moreEvidence').replace('{count}', String(latest.citations.length - 3))}
              </p>
            )}
          </div>
        </div>
      </Panel>

      <EscalateButton
        emphasized={Boolean(latest.escalate_recommended)}
        disabled={sending}
        onEscalate={onEscalate}
      />
      <CorpusNote />
    </div>
  )
}

function GuidanceCompact() {
  const { t } = useLanguage()
  return (
    <Panel title={t('chat.howWorksTitle')}>
      <ol className="list-decimal space-y-1 pl-4 text-sm text-ink-muted">
        <li>{t('chat.how1')}</li>
        <li>{t('chat.how2')}</li>
        <li>{t('chat.how3')}</li>
        <li>{t('chat.how4')}</li>
        <li>{t('chat.how5')}</li>
      </ol>
    </Panel>
  )
}

function CorpusNote() {
  const { t } = useLanguage()
  return (
    <Panel title={t('chat.corpusTitle')}>
      <p className="text-xs text-ink-muted">{t('chat.corpusBody')}</p>
    </Panel>
  )
}
