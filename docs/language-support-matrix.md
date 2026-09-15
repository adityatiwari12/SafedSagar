# Language support matrix

Source of truth in code: `apps/api/app/translation/languages.py`.

| Code | Native name | English name | Script | Direction | Detection | Translation |
|---|---|---|---|---|---|---|
| en | English | English | Latin | ltr | Yes (pivot - always "detected" trivially) | N/A (canonical) |
| hi | हिन्दी | Hindi | Devanagari | ltr | Yes | Scaffolded, sidecar not running |
| mr | मराठी | Marathi | Devanagari | ltr | Yes | Scaffolded, sidecar not running |
| bn | বাংলা | Bengali | Bengali | ltr | Yes | Scaffolded, sidecar not running |
| ta | தமிழ் | Tamil | Tamil | ltr | Yes | Scaffolded, sidecar not running |
| te | తెలుగు | Telugu | Telugu | ltr | Yes | Scaffolded, sidecar not running |
| gu | ગુજરાતી | Gujarati | Gujarati | ltr | Yes | Scaffolded, sidecar not running |
| kn | ಕನ್ನಡ | Kannada | Kannada | ltr | Yes | Scaffolded, sidecar not running |
| ml | മലയാളം | Malayalam | Malayalam | ltr | Yes | Scaffolded, sidecar not running |
| pa | ਪੰਜਾਬੀ | Punjabi | Gurmukhi | ltr | Yes | Scaffolded, sidecar not running |
| or | ଓଡ଼ିଆ | Odia | Odia | ltr | Yes | Scaffolded, sidecar not running |
| as | অসমীয়া | Assamese | Bengali | ltr | Yes | Scaffolded, sidecar not running |
| ur | اردو | Urdu | Arabic | **rtl** | Yes | Scaffolded, sidecar not running |

"Detection: Yes" means `language_detector.py` (py3langid) includes that
code in its restricted candidate set and was spot-checked on at least one
real sentence during Phase 1 build/test (see
`apps/api/tests/test_translation.py` for English and Marathi; the
remaining 11 use the same detector and code path, not per-language
special-casing, so they're expected to behave the same, but weren't each
individually spot-checked with a native sentence this pass).

"Translation: Scaffolded, sidecar not running" means: the HTTP contract,
language-tag mapping, and graceful degradation are implemented and
covered by tests that mock the provider (see
`test_translation_service_falls_back_when_provider_unavailable` etc.) -
but no request has yet been round-tripped through a live IndicTrans2
model for any of the 13 languages. Standing up
`services/indictrans2-sidecar/` is the next phase.

## RTL

Urdu (`ur`) is the only RTL language in scope. `languages.py` marks its
`direction` as `"rtl"` so the frontend (not yet built) can apply
`dir="rtl"` to the answer/input region only when `ur` is active - task
Section 8 is explicit that the rest of the app must stay LTR.

## Glossary coverage

All 20 terms listed in task Section 5 are present in
`apps/api/app/translation/glossary/terms.yaml` and protected from MT for
every language pair. None have a vetted localized string yet (see
"What's deferred" in `docs/multilingual-architecture.md`) - an unvetted
term is rendered in English inline rather than guessed.

## Known gap vs. CLAUDE.md

CLAUDE.md's build order (step 8) and `docs/product/functional-
requirements.md` (FR-12) scope multilingual to Hindi-only for the MVP,
via Bhashini. This matrix reflects the broader 13-language/IndicTrans2
scope that was explicitly requested for this build instead - flagged
here so the discrepancy is visible next to the thing it contradicts, not
just in a chat transcript.
