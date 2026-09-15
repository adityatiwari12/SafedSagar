"""Translation sidecar - NLLB-200 (facebook/nllb-200-distilled-600M).

Originally built around AI4Bharat's IndicTrans2, which turned out to be a
dead end on this stack: its `IndicTransToolkit` dependency ships no
Windows wheel and needs Cython to build from source (blocked by this
machine's Windows Application Control policy - see README.md), and its
three model checkpoints are gated on Hugging Face (an "auto"-approved but
still-manual click-through per repo, needing an account this deployment
doesn't have). Switched to NLLB-200: **ungated**, single model covers
every direction in our 13-language matrix (no separate en-indic/indic-en/
indic-indic checkpoints), and needs only `transformers` - no extra
toolkit. Still runs as its own Linux container for the same original
reason: PyTorch has no Windows wheel for this machine's Python 3.14.

Kept behind the same TranslationProvider HTTP contract
(app/translation/indictrans2_provider.py) - swapping the underlying model
again later (e.g. to IndicTrans2 if the gate friction goes away, or to
Bhashini) touches this file and that one, not the callers.
"""

from __future__ import annotations

import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Translation Sidecar (NLLB-200)")

MODEL_NAME = "facebook/nllb-200-distilled-600M"

# FLORES-200 tags NLLB-200 was trained on - the same tag set IndicTrans2
# used, so this mapping didn't need to change when the model did.
_FLORES_TAGS = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "mr": "mar_Deva",
    "bn": "ben_Beng",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "gu": "guj_Gujr",
    "kn": "kan_Knda",
    "ml": "mal_Mlym",
    "pa": "pan_Guru",
    "or": "ory_Orya",
    "as": "asm_Beng",
    "ur": "urd_Arab",
}

_lock = threading.Lock()
_state: dict = {}  # {"tokenizer": ..., "model": ...} once loaded


def _load() -> tuple:
    """Lazy singleton, loaded once on first request, never per-request
    (task Section 3: "Do not load the model per request")."""
    if _state:
        return _state["tokenizer"], _state["model"]
    with _lock:
        if _state:
            return _state["tokenizer"], _state["model"]
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float32)
        model.eval()
        _state["tokenizer"] = tokenizer
        _state["model"] = model
        return tokenizer, model


class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str


class TranslateResponse(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "model_loaded": bool(_state)}


@app.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    if payload.source_language not in _FLORES_TAGS or payload.target_language not in _FLORES_TAGS:
        raise HTTPException(status_code=400, detail="Unsupported language code")

    tokenizer, model = _load()

    tokenizer.src_lang = _FLORES_TAGS[payload.source_language]
    inputs = tokenizer(payload.text, return_tensors="pt", truncation=True)

    import torch

    with torch.no_grad():
        generated = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(_FLORES_TAGS[payload.target_language]),
            max_length=256,
            num_beams=5,
        )

    translated = tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
    return TranslateResponse(text=translated)
