"""Translation sidecar - IndicTrans2 (ai4bharat), NLLB-200 fallback.

Backend selection: `TRANSLATION_BACKEND` env var ("indictrans2" | "nllb"),
defaulting to "indictrans2" when `HF_TOKEN` is set, else "nllb". IndicTrans2's
checkpoints are gated on Hugging Face ("auto"-approved but still needs a
logged-in account that has clicked "accept" on each model page once,
plus a token with read access) - if the token is missing or the account
hasn't accepted the gate yet, `_load()` falls back to NLLB-200 rather than
hard-failing the container. See README.md "Model: IndicTrans2, with an
NLLB-200 fallback" for the full history of why this was originally
believed to be a dead end on this stack (it wasn't - that applied to the
Windows host, not this Linux container).

IndicTrans2 ships two direction-specific checkpoints (no single
multi-directional model like NLLB): `indictrans2-en-indic-dist-200M` for
English -> any Indic language, and `indictrans2-indic-en-dist-200M` for
Indic -> English. An Indic -> Indic request is served by pivoting through
English with both models rather than loading the third (indic-indic,
320M) checkpoint - keeps resident RAM to two 200M models instead of three
on this 16GB dev machine.
"""

from __future__ import annotations

import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Translation Sidecar")

NLLB_MODEL = "facebook/nllb-200-distilled-600M"
INDICTRANS2_EN_INDIC = "ai4bharat/indictrans2-en-indic-dist-200M"
INDICTRANS2_INDIC_EN = "ai4bharat/indictrans2-indic-en-dist-200M"

HF_TOKEN = os.environ.get("HF_TOKEN") or None
BACKEND = os.environ.get("TRANSLATION_BACKEND") or ("indictrans2" if HF_TOKEN else "nllb")

# FLORES-200 tags - both NLLB and IndicTrans2 (via IndicTransToolkit) use
# this same tag set, so one mapping serves either backend.
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
_state: dict = {}  # populated once by _load(); "backend" key tells translate() which path to use


def _load_nllb() -> dict:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(NLLB_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL, torch_dtype=torch.float32)
    model.eval()
    return {"backend": "nllb", "tokenizer": tokenizer, "model": model}


def _load_indictrans2() -> dict:
    import torch
    from IndicTransToolkit.processor import IndicProcessor
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    auth = {"token": HF_TOKEN, "trust_remote_code": True}

    en_indic_tokenizer = AutoTokenizer.from_pretrained(INDICTRANS2_EN_INDIC, **auth)
    en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(
        INDICTRANS2_EN_INDIC, torch_dtype=torch.float32, **auth
    )
    en_indic_model.eval()

    indic_en_tokenizer = AutoTokenizer.from_pretrained(INDICTRANS2_INDIC_EN, **auth)
    indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(
        INDICTRANS2_INDIC_EN, torch_dtype=torch.float32, **auth
    )
    indic_en_model.eval()

    return {
        "backend": "indictrans2",
        "processor": IndicProcessor(inference=True),
        "en_indic": (en_indic_tokenizer, en_indic_model),
        "indic_en": (indic_en_tokenizer, indic_en_model),
    }


def _load() -> dict:
    """Lazy singleton, loaded once on first request, never per-request
    (task Section 3: "Do not load the model per request")."""
    if _state:
        return _state
    with _lock:
        if _state:
            return _state
        if BACKEND == "indictrans2":
            try:
                _state.update(_load_indictrans2())
                return _state
            except Exception as exc:  # gated/network/version mismatch - degrade, don't hard-fail
                print(f"[sidecar] IndicTrans2 load failed ({exc!r}); falling back to NLLB-200")
        _state.update(_load_nllb())
        return _state


class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str


class TranslateResponse(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": bool(_state),
        "backend": _state.get("backend", BACKEND),
    }


def _translate_nllb(text: str, src_tag: str, tgt_tag: str) -> str:
    import torch

    tokenizer, model = _state["tokenizer"], _state["model"]
    tokenizer.src_lang = src_tag
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_tag),
            max_length=256,
            num_beams=5,
        )
    return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]


def _translate_indictrans2_hop(text: str, src_tag: str, tgt_tag: str, tokenizer_model: tuple) -> str:
    import torch

    tokenizer, model = tokenizer_model
    processor = _state["processor"]

    batch = processor.preprocess_batch([text], src_lang=src_tag, tgt_lang=tgt_tag)
    inputs = tokenizer(batch, truncation=True, padding="longest", return_tensors="pt")
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            use_cache=True,
            min_length=0,
            max_length=256,
            num_beams=5,
        )
    decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)
    return processor.postprocess_batch(decoded, lang=tgt_tag)[0]


def _translate_indictrans2(text: str, src_tag: str, tgt_tag: str) -> str:
    if src_tag == "eng_Latn":
        return _translate_indictrans2_hop(text, src_tag, tgt_tag, _state["en_indic"])
    if tgt_tag == "eng_Latn":
        return _translate_indictrans2_hop(text, src_tag, tgt_tag, _state["indic_en"])
    # indic -> indic: pivot through English (no indic-indic checkpoint loaded)
    english = _translate_indictrans2_hop(text, src_tag, "eng_Latn", _state["indic_en"])
    return _translate_indictrans2_hop(english, "eng_Latn", tgt_tag, _state["en_indic"])


@app.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    if payload.source_language not in _FLORES_TAGS or payload.target_language not in _FLORES_TAGS:
        raise HTTPException(status_code=400, detail="Unsupported language code")

    state = _load()
    src_tag = _FLORES_TAGS[payload.source_language]
    tgt_tag = _FLORES_TAGS[payload.target_language]

    if state["backend"] == "indictrans2":
        translated = _translate_indictrans2(payload.text, src_tag, tgt_tag)
    else:
        translated = _translate_nllb(payload.text, src_tag, tgt_tag)

    return TranslateResponse(text=translated)
