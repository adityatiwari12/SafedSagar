# Translation sidecar

Runs as its own Docker container (Linux, via Docker Desktop's Linux VM
backend), separate from `apps/api`, because PyTorch ships no Windows
wheel for this machine's Python 3.14 (only the experimental
free-threaded `cp314t` build, which nothing else here targets). Same
infra pattern as `postgres`/`chromadb` in `infra/docker-compose.yml`, not
a new architectural layer - not in tension with CLAUDE.md's "one FastAPI
service" rule (that rule is about the orchestration/reasoning graph, not
about which process a model runtime with an incompatible Python
requirement runs in).

## Model: IndicTrans2, with an NLLB-200 fallback

This was originally built around AI4Bharat's IndicTrans2 and looked like
a dead end because of two things checked against the **Windows host**:

1. `IndicTransToolkit` (its required pre/post-processing library)
   appeared to ship no Windows wheel.
2. Its model checkpoints are gated on Hugging Face - "auto"-approved,
   but still needs a logged-in account to click through each repo page
   once.

(1) doesn't actually apply here: this sidecar runs inside a **Linux**
container, and `IndicTransToolkit` ships a prebuilt manylinux wheel for
cp312 - no Cython compiler needed, no Windows Application Control policy
in the way. (2) is real but is a one-time human step, not a code
blocker - see Setup below.

The sidecar auto-detects which backend to run:

- `HF_TOKEN` set (and the account has accepted the two gated model
  pages) → **IndicTrans2** (`indictrans2-en-indic-dist-200M` for
  English→Indic, `indictrans2-indic-en-dist-200M` for Indic→English;
  Indic→Indic pivots through English using both, so only two 200M
  checkpoints are resident instead of three).
- `HF_TOKEN` unset, or the IndicTrans2 load fails for any reason (token
  not yet accepted on HF, network hiccup, etc.) → falls back to
  **`facebook/nllb-200-distilled-600M`** at first request, logging why.
  Confirmed ungated, one model covers every direction in the 13-language
  matrix.

`TRANSLATION_BACKEND=indictrans2|nllb` overrides the auto-detect either
way (e.g. force `nllb` even with a token set, to save RAM).

Both backends use the same FLORES-200 language tags, so
`app/translation/languages.py`'s code→tag mapping needed no change
either way.

License note: NLLB-200's distilled checkpoints are `cc-by-nc-4.0`
(non-commercial) - fine for this SIH prototype, but flag it if this ever
moves toward commercial deployment. IndicTrans2 is MIT.

## Status

Running. `apps/api/app/translation/indictrans2_provider.py` points at
`http://localhost:8600` (configurable via `INDICTRANS2_SIDECAR_URL`) and
degrades gracefully - `translation_status: "unavailable"`,
`needs_human_review: true` - if this container isn't up.

## Setup

From the repo root, this is one of the services in
`infra/docker-compose.yml`:

```bash
docker compose -f infra/docker-compose.yml up -d --build indictrans2-sidecar
```

**To run real IndicTrans2** (skip this for the NLLB-200 fallback):

1. Log into a Hugging Face account, visit
   `ai4bharat/indictrans2-en-indic-dist-200M` and
   `ai4bharat/indictrans2-indic-en-dist-200M`, click "Agree and access
   repository" on each (auto-approved, one-time).
2. Create a read-scoped token at huggingface.co/settings/tokens.
3. Set it before bringing the container up, e.g. in `infra/.env`:

   ```env
   HF_TOKEN=hf_...
   ```

Or standalone:

```bash
cd services/indictrans2-sidecar
docker build -t ipsakti-indictrans2-sidecar .
docker run -p 8600:8600 -e HF_TOKEN=hf_... \
  -v indictrans2_models:/root/.cache/huggingface ipsakti-indictrans2-sidecar
```

First `/translate` call downloads the active backend's weights from the
Hugging Face Hub (~800MB for both IndicTrans2 checkpoints, ~2.4GB for
NLLB-200) and keeps them resident in RAM, not per-request (see `_load()`'s
lazy-singleton comment in `app.py`). The `indictrans2_models` volume
caches them across container restarts.

## Hardware note

This dev machine has 16GB RAM total and was observed with well under 1GB
free while Ollama's `llama3.2` was loaded (see `apps/api/.env.example`'s
note on `gpt-oss:20b` being too slow/unreliable here). Two resident 200M
IndicTrans2 models are lighter than the single 600M NLLB-200 model, but
either way, start this container only when translation is actually being
tested, not as an always-on background service, if RAM is tight.

## API

`POST /translate`

```json
{"text": "...", "source_language": "en", "target_language": "hi"}
```

`GET /health` - `{"status": "ok", "model_loaded": true|false, "backend": "indictrans2"|"nllb"}`.

## Language code mapping

The main API uses plain ISO 639-1 codes (`hi`, `mr`, ...); both backends
expect FLORES-200 tags (`hin_Deva`, `mar_Deva`, ...). The mapping lives in
`_FLORES_TAGS` in `app.py` - keep it in sync with
`apps/api/app/translation/languages.py`'s `LANGUAGES` dict if either list
changes.
