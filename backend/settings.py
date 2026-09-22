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

    # Shared secret required on every mutating request (POST/PATCH/PUT/DELETE),
    # checked by the X-MAIDA-Admin-Key header (see main.py:admin_key_guard).
    # Left empty here on purpose: main.py generates and logs a random one at
    # startup when unset, so a deployment is never silently wide open, and a
    # fresh `docker compose up` still works without extra setup (the operator
    # reads the key from the container logs). Set this explicitly in
    # production so the key survives a restart.
    maida_admin_key: str = ""

    # Path of the SQLite file backing the study store. Records used to live in
    # a module-level dict and were lost on every restart; a file-backed store
    # means a crashed or reloaded process no longer destroys verified work.
    maida_db_path: str = "maida.db"

    # Demo mode, off by default. Reported via /api/health; also tells the
    # admin-key guard in main.py to stand down, since demo/run_defense.py
    # already protects every mutation with its own presenter PIN. (The
    # rehearsed-fallback-on-no-LLM behaviour once gated by this flag was
    # removed in the E1 fix - extraction has exactly two modes now, live or
    # unavailable, demo or not; see main.py:health_check.)
    maida_demo_mode: bool = False

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
