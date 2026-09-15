"""Application settings and configuration."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    chroma_base_url: str = "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database"
    chroma_collection: str = "source_chunks"

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


settings = Settings()
