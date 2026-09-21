import { ReactNode } from 'react'
import { useLanguage } from '../i18n/LanguageContext'

export function MessageBubble({
  role,
  children,
}: {
  role: 'user' | 'assistant'
  children: ReactNode
}) {
  const { t } = useLanguage()
  const isUser = role === 'user'

  if (isUser) {
    return (
      <div className="border-l-2 border-saffron bg-ivory/80 px-4 py-3">
        <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
          {t('chat.queryLabel')}
        </p>
        <div className="text-sm leading-relaxed text-ink">{children}</div>
      </div>
    )
  }

  return (
    <div>
      <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-ink-faint">
        {t('chat.assessmentLabel')}
      </p>
      {children}
    </div>
  )
}
