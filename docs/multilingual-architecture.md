# Multilingual architecture

Status: language abstraction layer, DB schema, `/chat` wiring, frontend
selector/RTL, and the translation sidecar are all implemented and
running. See [What's deferred](#whats-deferred) for what isn't.

## Why this exists, and the scope tension it sits in

CLAUDE.md's own build order (step 8) scopes multilingual to "one real
path (Hindi only)... don't attempt full Bhashini coverage under time
pressure," and `docs/product/functional-requirements.md` FR-12 confirms
that scope. This build was explicitly requested to cover all 13 target
languages instead. That's a real scope increase over what's committed
elsewhere in the repo's docs - flagging it here so it isn't mistaken for
what CLAUDE.md describes.

## Pipeline

```
User query (any of 13 languages, or English)
  -> language detection (py3langid, restricted to the 13 supported codes)
  -> if non-English: translate to canonical English (sidecar)
  -> existing classify_product -> route_jurisdiction -> route_ip_type
     -> retrieve -> rerank -> reason_and_cite -> validate_citations
     -> score_confidence -> escalate_if_needed   [unchanged - see graph.py]
  -> canonical English answer, with citations already validated against
     the retrieved chunk set
  -> if target language != English: translate the answer (sidecar)
  -> translation validation (structural: section/rule/article refs, URLs,
     glossary placeholders)
  -> if validation fails or the provider is unavailable: fall back to the
     canonical English answer, flag needs_human_review
  -> final response
```

Citation validation happens strictly before translation - the graph's
`validate_citations` node only ever sees the canonical English answer and
the English-language retrieved chunks. Translation never touches which
citations are considered valid; it only translates already-validated
prose.

## Why English is the pivot, not a multilingual embedding model

The corpus (`apps/api/app/graph/nodes/retrieve.py`, ChromaDB via
`nomic-embed-text`) is English-only. Rather than re-embed the entire
corpus with a multilingual model (task Section 4 explicitly rules this
out - "do NOT create separate knowledge bases per language"), a non-
English query is translated to English *before* retrieval, so retrieval,
reranking, and reasoning are unchanged from the existing English-only
pipeline.

## Components (`apps/api/app/translation/`)

| File | Responsibility |
|---|---|
| `languages.py` | The 13-language metadata table (native name, English name, direction, script) - single source of truth, mirrored on the frontend by `apps/web/src/api/languages.ts`. |
| `language_detector.py` | `detect_language(text) -> (code, confidence)` via py3langid, restricted to the 13 codes. Pure Python, no native/compiled deps. |
| `provider.py` | `TranslationProvider` ABC - `translate()`, `supported_languages()`, and a default `detect()` that delegates to `language_detector`. |
| `indictrans2_provider.py` | Calls the sidecar over HTTP. Named for its original target model (see [Model history](#model-history-indictrans2--nllb-200)) - still the only file that knows which model the sidecar actually runs. Raises `TranslationUnavailableError` if unreachable - never fabricates a translation. |
| `glossary_service.py` | Loads `glossary/terms.yaml`; `protect()`/`restore()` swap protected legal terms for opaque placeholder tokens around a `translate()` call so MT can't paraphrase them. |
| `translation_validator.py` | Rule-based post-translation checks: section/rule/article references, URLs, and glossary placeholders must match before/after. |
| `translation_service.py` | The facade `chat/router.py` and `/translate` call - orchestrates protect → translate → restore → validate → safe-fallback-on-failure. |
| `router.py` / `schemas.py` | `POST /language/detect`, `POST /translate`. |

## Why translation runs as a separate process (the sidecar)

`apps/api`'s venv is pinned to Python 3.14. PyTorch has no Windows wheel
for plain `cp314` (checked directly against PyPI's file listing - only
`cp314t`, the experimental free-threaded build, exists, and nothing else
in this stack targets it). Translation runs in its own Docker container
instead (`services/indictrans2-sidecar/`), called over HTTP -
architecturally the same shape as the existing Ollama and ChromaDB
integrations, not a new microservices layer. `IndicTrans2Provider` is the
only file in `apps/api` that knows this detail; everything else talks to
`TranslationProvider`.

### Model history: IndicTrans2 → NLLB-200

The task asked for AI4Bharat IndicTrans2 specifically. That was tried
first and hit two dead ends on this machine, in order:

1. A Python-3.12-venv-on-Windows attempt hit IndicTrans2's required
   `IndicTransToolkit` library shipping no Windows wheel at all (only
   manylinux/macOS/PyPy), with a source build needing Cython - blocked by
   this machine's Windows Application Control policy. Moved the sidecar
   into a Docker container (Linux) to sidestep this.
2. Inside the container, all three IndicTrans2 checkpoints
   (`ai4bharat/indictrans2-{en-indic,indic-en,indic-indic}-dist-*`) turned
   out to be **gated** on Hugging Face - confirmed via the HF API
   (`"gated": "auto"`) - needing a logged-in account to click "Agree and
   access repository" on each of three pages before anything downloads.
   That's an account action outside what this build could do
   autonomously.

Rather than block the feature on that manual step, the sidecar now runs
**`facebook/nllb-200-distilled-600M`** - confirmed ungated via the same
HF API check, single model covers every direction in the 13-language
matrix (IndicTrans2 needed three separate checkpoints for en→indic,
indic→en, indic→indic), and uses the same FLORES-200 language tags
IndicTrans2 used, so `languages.py`'s code mapping didn't need to change.
License: `cc-by-nc-4.0` (non-commercial) - fine for this prototype, flag
it before any commercial deployment. See
`services/indictrans2-sidecar/README.md` for the full writeup.

### Sidecar status

Running (`docker compose -f infra/docker-compose.yml up -d indictrans2-sidecar`,
port 8600). No account or token needed. First `/translate` call downloads
the model (~2.4GB) and keeps it resident; a Docker volume caches it
across restarts. If the container isn't up, every non-English request
still degrades safely: `translation_status: "unavailable"`,
`needs_human_review: true`, canonical English returned instead of
nothing.

## DB schema additions

- `users.preferred_language` - a saved fallback for low-confidence detection.
- `conversations.language` - set from the first turn, reused as the
  fallback for later low-confidence turns in the same conversation.
- `messages.content` - always canonical English (what history-folding and
  the graph actually see, regardless of the turn's language).
- `messages.display_text` - what the user actually saw/typed: raw input
  for a user turn, localized answer for an assistant turn. Separate from
  `content` so the chat-history view (`GET /conversations/{id}/messages`)
  renders what actually happened, not the internal English pivot text.
- `messages.response_json` - the full `ChatTurnResponse` an assistant
  message produced (citations, classification, confidence, ...), so
  reopening a past conversation re-renders identically to when it was
  first shown, not just plain text.
- `messages.language` - the turn's language.

Migrations: `a9ef26176043_add_language_columns.py`,
`bac77a07f67e_messages_add_display_text_response_.py`.

## `/chat` response additions (additive - old fields unchanged)

```json
{
  "answer": "<localized answer, or English if language=en/unset - unchanged behavior for existing callers>",
  "detected_language": "mr",
  "canonical_query": "<English-translated query>",
  "canonical_answer": "<English answer before translation>",
  "translation_status": "verified | not_needed | failed | unavailable",
  "needs_human_review": false
}
```

`needs_human_review` here is a **translation-quality** signal, distinct
from `escalate_recommended` (a legal-confidence signal from
`escalate_if_needed`). A response can have low legal confidence and
perfect translation, or the reverse.

## Fallback strategy (task Section 7)

On a validation failure or provider outage, the service returns the
**canonical English text unmodified**, not a best-effort or partially-
translated result, and sets `needs_human_review: true`. This does not
implement the "retry translation" step from the spec's fallback ladder -
a deterministic MT call fails the same way on retry, so retrying only
adds latency for no benefit; retry becomes worth adding once a stochastic
(LLM-based) translation path exists whose output could plausibly vary
between attempts.

## Privacy

Translation runs locally (the sidecar), so no query text leaves this
deployment for translation. This matters if a hosted/cloud translation
provider is ever added behind the same `TranslationProvider` interface -
per the task's explicit constraint, that must not become the default.

## What's deferred

- **Multilingual evaluation suite** (task Section 10).
- **Semantic translation validation** - negation, modality (may/must/
  shall/should/cannot). The validator is structural only (section
  numbers, URLs, glossary placeholders); semantic checks need an
  LLM-judge call, deliberately not added yet to keep the dependency
  surface small.
- **Vetted glossary translations** - `glossary/terms.yaml` protects all
  20 listed terms from MT but has no localized strings for any of them
  (task Section 5: "Never invent translations" - an empty,
  reviewed-later table is the correct state, not a gap).
- **Bhashini integration** - the provider abstraction is ready for it
  (implement `TranslationProvider`, swap it into `TranslationService`),
  but no Bhashini code exists.
- **Live end-to-end verification of a real translated `/chat` turn** -
  the sidecar is up and `/health` is green, but a full non-English
  `/chat` round-trip through it hasn't been exercised yet in this repo.
