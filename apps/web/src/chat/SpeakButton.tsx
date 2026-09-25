import { useLanguage } from '../i18n/LanguageContext'
import { useTextToSpeech } from './useTextToSpeech'

/** Read-aloud toggle for one assistant message, in the conversation's
 * active language (see useTextToSpeech for voice-availability caveats). */
export function SpeakButton({ text }: { text: string }) {
  const { t, language } = useLanguage()
  const { supported, speaking, speak, cancel } = useTextToSpeech()

  if (!supported) return null

  return (
    <button
      type="button"
      aria-label={speaking ? t('chat.speakStop') : t('chat.speakStart')}
      title={speaking ? t('chat.speakStop') : t('chat.speakStart')}
      onClick={() => (speaking ? cancel() : speak(text, language))}
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors ${
        speaking
          ? 'border-saffron bg-saffron text-white'
          : 'border-surface-border bg-white text-ink-faint hover:border-saffron hover:text-saffron-deep'
      }`}
    >
      {speaking ? (
        <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
          <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
          <path
            d="M4 9v6h4l5 4V5L8 9H4Z"
            fill="currentColor"
          />
          <path
            d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      )}
    </button>
  )
}
