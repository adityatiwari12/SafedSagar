import type { LanguageCode } from '../api/languages'
import type { MessageKey, Messages } from './types'
import { en } from './messages/en'
import { hi } from './messages/hi'
import { regional } from './messages/regional'

const CATALOGS: Record<LanguageCode, Messages> = {
  en,
  hi,
  mr: regional.mr,
  bn: regional.bn,
  ta: regional.ta,
  te: regional.te,
  gu: regional.gu,
  kn: regional.kn,
  ml: regional.ml,
  pa: regional.pa,
  or: regional.or,
  as: regional.as,
  ur: regional.ur,
}

export function getMessages(code: LanguageCode): Messages {
  return CATALOGS[code] ?? en
}

export function t(messages: Messages, key: MessageKey): string {
  const [group, field] = key.split('.') as [keyof Messages, string]
  const section = messages[group] as Record<string, string> | undefined
  const value = section?.[field]
  if (typeof value === 'string') return value
  const fallback = (en[group] as Record<string, string> | undefined)?.[field]
  return fallback ?? key
}
