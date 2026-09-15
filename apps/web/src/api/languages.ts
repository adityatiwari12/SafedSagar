// Mirrors apps/api/app/translation/languages.py - single source of truth
// for the 13 supported languages on the frontend side. Keep in sync if
// the backend list changes.

export type LanguageCode =
  | 'en'
  | 'hi'
  | 'mr'
  | 'bn'
  | 'ta'
  | 'te'
  | 'gu'
  | 'kn'
  | 'ml'
  | 'pa'
  | 'or'
  | 'as'
  | 'ur'

export interface LanguageInfo {
  code: LanguageCode
  nativeName: string
  englishName: string
  direction: 'ltr' | 'rtl'
}

export const LANGUAGES: LanguageInfo[] = [
  { code: 'en', nativeName: 'English', englishName: 'English', direction: 'ltr' },
  { code: 'hi', nativeName: 'हिन्दी', englishName: 'Hindi', direction: 'ltr' },
  { code: 'mr', nativeName: 'मराठी', englishName: 'Marathi', direction: 'ltr' },
  { code: 'bn', nativeName: 'বাংলা', englishName: 'Bengali', direction: 'ltr' },
  { code: 'ta', nativeName: 'தமிழ்', englishName: 'Tamil', direction: 'ltr' },
  { code: 'te', nativeName: 'తెలుగు', englishName: 'Telugu', direction: 'ltr' },
  { code: 'gu', nativeName: 'ગુજરાતી', englishName: 'Gujarati', direction: 'ltr' },
  { code: 'kn', nativeName: 'ಕನ್ನಡ', englishName: 'Kannada', direction: 'ltr' },
  { code: 'ml', nativeName: 'മലയാളം', englishName: 'Malayalam', direction: 'ltr' },
  { code: 'pa', nativeName: 'ਪੰਜਾਬੀ', englishName: 'Punjabi', direction: 'ltr' },
  { code: 'or', nativeName: 'ଓଡ଼ିଆ', englishName: 'Odia', direction: 'ltr' },
  { code: 'as', nativeName: 'অসমীয়া', englishName: 'Assamese', direction: 'ltr' },
  { code: 'ur', nativeName: 'اردو', englishName: 'Urdu', direction: 'rtl' },
]

const BY_CODE = new Map(LANGUAGES.map((l) => [l.code, l]))

export function getLanguage(code: LanguageCode): LanguageInfo {
  return BY_CODE.get(code) ?? LANGUAGES[0]
}

export function isRtl(code: LanguageCode): boolean {
  return getLanguage(code).direction === 'rtl'
}

export function isSupportedLanguage(code: string | null | undefined): code is LanguageCode {
  return !!code && BY_CODE.has(code as LanguageCode)
}
