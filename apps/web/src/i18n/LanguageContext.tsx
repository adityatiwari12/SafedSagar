import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { LanguageCode, getLanguage, isSupportedLanguage } from '../api/languages'
import { getMessages, t as translate } from './catalog'
import type { MessageKey, Messages } from './types'

export const LANGUAGE_STORAGE_KEY = 'ipsakti.language'

type LanguageContextValue = {
  language: LanguageCode
  setLanguage: (code: LanguageCode) => void
  messages: Messages
  t: (key: MessageKey) => string
  direction: 'ltr' | 'rtl'
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function loadStoredLanguage(): LanguageCode {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    if (isSupportedLanguage(stored)) return stored
  } catch {
    // private browsing / blocked storage
  }
  return 'en'
}

function persistLanguage(code: LanguageCode) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, code)
  } catch {
    // convenience only
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>(() =>
    typeof window === 'undefined' ? 'en' : loadStoredLanguage(),
  )

  const setLanguage = useCallback((code: LanguageCode) => {
    persistLanguage(code)
    setLanguageState(code)
  }, [])

  const messages = useMemo(() => getMessages(language), [language])
  const direction = getLanguage(language).direction

  const t = useCallback((key: MessageKey) => translate(messages, key), [messages])

  useEffect(() => {
    document.documentElement.lang = language
    // Keep document LTR; RTL is scoped to the chat panel for Urdu so shell
    // chrome (header, breadcrumbs) does not mirror unexpectedly.
    document.documentElement.dir = 'ltr'
  }, [language])

  const value = useMemo(
    () => ({ language, setLanguage, messages, t, direction }),
    [language, setLanguage, messages, t, direction],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be used within LanguageProvider')
  }
  return ctx
}
