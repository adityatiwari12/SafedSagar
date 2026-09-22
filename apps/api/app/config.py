"""Application settings and configuration."""

import logging
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_MIN_JWT_SECRET_LENGTH = 32
_PLACEHOLDER_MARKER = "change-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_generate_model: str = "llama3.2"
    # Context window for generation calls. Ollama's own default is 2048
    # tokens, and it silently truncates anything longer from the front -
    # which is where the reason_and_cite prompt keeps its rules (cite only
    # numbered chunks, return JSON, answer the actual question). Real
    # answer prompts run ~4.5-5.2k tokens, so at the default every answer
    # was generated from less than half its prompt. 8192 fits them with
    # headroom for the response; llama3.2 supports far more, but on CPU
    # the KV cache (~110KB/token for a 3B model) makes much larger costly.
    ollama_num_ctx: int = 8192
    # Optional override used only by reason_and_cite (the final-answer call,
    # where quality matters more than latency) - e.g. "gpt-oss:20b" for a
    # thinking-model quality bump. classify_product/routers stay on the fast
    # default: a thinking model adds tens of seconds per call on CPU-only
    # hardware, unacceptable for the quick categorical calls.
    ollama_reasoning_model: str | None = None

    # Generation provider: "ollama" (default) or "cloud" (OpenAI-compatible).
    llm_provider: str = "ollama"
    # Optional override used only by reason_and_cite; classifiers stay on llm_provider.
    llm_reasoning_provider: str | None = None
    cloud_llm_base_url: str | None = None
    cloud_llm_api_key: str | None = None
    cloud_llm_model: str | None = None
    # Some OpenAI-compatible providers reject `response_format:
    # {"type":"json_object"}` outright (400/422 mentioning response_format).
    # When true (default), cloud_client sends it and, if a provider rejects
    # it, retries once without it and extracts JSON from the (possibly
    # ```json-fenced) text instead. Set false to skip straight to that mode
    # for a provider already known not to support it.
    cloud_llm_json_mode: bool = True
    # If the cloud provider fails after its retry budget (network error,
    # expired/invalid key past the fail-fast check, persistent 5xx, etc.),
    # fall back to local Ollama for that call rather than raising - a demo
    # must not die because a cloud API key expired or the network dropped.
    # generate.get_last_call_metadata().fallback_used reports when this fired.
    llm_fallback_to_local: bool = True

    chroma_base_url: str = "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database"
    chroma_collection: str = "source_chunks"

    # IndicTrans2 sidecar (services/indictrans2-sidecar/) - a separate
    # Python 3.12 process, since this venv's Python 3.14 has no PyTorch
    # wheel on Windows. See app/translation/indictrans2_provider.py.
    indictrans2_sidecar_url: str = "http://localhost:8600"

    # Secure document storage (Phase 28) - app.documents.storage.
    # LocalFilesystemStorage root. No cloud storage credentials exist in
    # this project yet, so uploads land on local disk behind a small
    # StorageBackend interface; swapping in real object storage later is a
    # one-class change, not a rewrite.
    document_storage_root: str = "./data/documents"
    document_max_upload_bytes: int = 20 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
    )

    @field_validator("jwt_secret")
    @classmethod
    def _reject_weak_secret(cls, v: str) -> str:
        # .env.example ships a placeholder so `cp .env.example .env` must
        # not silently boot a real app signing tokens with a public key.
        if len(v) < _MIN_JWT_SECRET_LENGTH or _PLACEHOLDER_MARKER in v:
            raise ValueError(
                f"JWT_SECRET must be a random value of at least "
                f"{_MIN_JWT_SECRET_LENGTH} characters, not the placeholder"
            )
        return v

    @model_validator(mode="after")
    def _check_cloud_llm_configured(self) -> "Settings":
        # Fail fast if a cloud provider is selected (either as the default
        # generation provider or just for reason_and_cite) but isn't actually
        # configured - a misconfigured provider should be caught at boot, not
        # on the first request. If llm_fallback_to_local is on, every cloud
        # call would just fail-and-fall-back-to-Ollama anyway (see
        # app/llm/generate.py), so don't crash the whole API over an optional
        # provider - warn loudly instead and let it run local.
        uses_cloud = self.llm_provider == "cloud" or self.llm_reasoning_provider == "cloud"
        if not uses_cloud:
            return self
        missing = [
            name
            for name, value in (
                ("CLOUD_LLM_BASE_URL", self.cloud_llm_base_url),
                ("CLOUD_LLM_MODEL", self.cloud_llm_model),
            )
            if not value
        ]
        if not missing:
            return self
        message = (
            f"Cloud LLM provider selected (LLM_PROVIDER/LLM_REASONING_PROVIDER=cloud) "
            f"but missing: {', '.join(missing)}."
        )
        if self.llm_fallback_to_local:
            logger.warning(
                "%s LLM_FALLBACK_TO_LOCAL is on, so cloud calls will fail over to "
                "Ollama at request time - fix this before a real demo.",
                message,
            )
        else:
            raise ValueError(
                f"{message} Set them, or set LLM_FALLBACK_TO_LOCAL=true to run on "
                f"Ollama instead."
            )
        return self


settings = Settings()
