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

## Model: NLLB-200, not IndicTrans2

The directory name is a holdover - this originally tried to run
AI4Bharat's IndicTrans2 and hit two dead ends on this stack:

1. `IndicTransToolkit` (its required pre/post-processing library) ships
   no Windows wheel at all (checked its PyPI file listing directly), and
   building it from source needs Cython, which this machine's Windows
   Application Control policy blocks outright.
2. All three IndicTrans2 model checkpoints are gated on Hugging Face -
   "auto"-approved, but still needs a logged-in account to click through
   three separate repo pages before anything downloads.

Switched to **`facebook/nllb-200-distilled-600M`** instead: confirmed
ungated via the HF API, one model covers every direction in the
13-language matrix (no separate en→indic/indic→en/indic→indic
checkpoints), and it needs only `transformers` - no extra toolkit. Uses
the same FLORES-200 language tags IndicTrans2 used, so
`app/translation/languages.py`'s code→tag mapping didn't need to change.

License note: NLLB-200's distilled checkpoints are `cc-by-nc-4.0`
(non-commercial) - fine for this SIH prototype, but flag it if this ever
moves toward a commercial deployment.

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

Or standalone:

```bash
cd services/indictrans2-sidecar
docker build -t ipsakti-indictrans2-sidecar .
docker run -p 8600:8600 -v indictrans2_models:/root/.cache/huggingface ipsakti-indictrans2-sidecar
```

No account or token needed - the model is public. First `/translate`
call downloads it from the Hugging Face Hub (~2.4GB) and keeps it
resident in RAM, not per-request (see `_load()`'s lazy-singleton comment
in `app.py`). The `indictrans2_models` volume caches it across container
restarts.

## Hardware note

This dev machine has 16GB RAM total and was observed with well under 1GB
free while Ollama's `llama3.2` was loaded (see `apps/api/.env.example`'s
note on `gpt-oss:20b` being too slow/unreliable here). One 600M-param
model is a single resident model now (simpler than the three-checkpoint
IndicTrans2 plan), but still worth starting this container only when
translation is actually being tested, not as an always-on background
service, if RAM is tight.

## API

`POST /translate`

```json
{"text": "...", "source_language": "en", "target_language": "hi"}
```

`GET /health` - `{"status": "ok", "model_loaded": true|false}`.

## Language code mapping

The main API uses plain ISO 639-1 codes (`hi`, `mr`, ...); NLLB expects
FLORES-200 tags (`hin_Deva`, `mar_Deva`, ...). The mapping lives in
`_FLORES_TAGS` in `app.py` - keep it in sync with
`apps/api/app/translation/languages.py`'s `LANGUAGES` dict if either list
changes.
