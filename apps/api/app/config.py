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
