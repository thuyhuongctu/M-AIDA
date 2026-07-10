"""
Application settings loaded from environment variables / .env file.

Uses pydantic-settings so every value is validated at startup. Missing
required values produce a clear error rather than a silent failure at runtime.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """M-AIDA runtime configuration.

    The public configuration uses provider-neutral names (`LLM_*`). Legacy
    provider-specific variables remain accepted for backward compatibility.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Provider-neutral public setting. The current adapter remains compatible
    # with existing Anthropic-compatible deployments.
    llm_provider: str = "anthropic"

    # Backward-compatible field names used by the existing app entry point.
    # They can now be populated by provider-neutral LLM_* variables as well.
    anthropic_api_key: str = Field(
        default="", validation_alias=AliasChoices("ANTHROPIC_API_KEY", "LLM_API_KEY")
    )
    anthropic_model: str = Field(
        default="", validation_alias=AliasChoices("ANTHROPIC_MODEL", "LLM_MODEL")
    )

    notion_token: str = ""
    notion_database_id: str = ""
    maida_port: int = 8765

    # Allowed CORS origins (comma-separated in env; pydantic-settings handles list)
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def resolved_model(self) -> str:
        """Return the configured model id, if one was supplied by the researcher."""
        return self.anthropic_model


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance, creating it on first call."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings
