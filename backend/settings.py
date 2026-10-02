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

    # ------------------------------------------------------------------
    # 8.0 (cloud): identity, data isolation, credits
    # ------------------------------------------------------------------
    # How callers are identified:
    #   admin_key - single operator, shared X-MAIDA-Admin-Key on mutations
    #               (the 7.2.x behaviour; default so every existing deployment,
    #               the Windows runner and the Defense App keep working).
    #   supabase  - multi-user SaaS: every /api route (except /api/health and
    #               /api/config) needs "Authorization: Bearer <Supabase JWT>".
    #   mock      - like supabase but tokens are minted locally by
    #               POST /api/auth/mock-login; for tests and e2e only.
    maida_auth_mode: str = "admin_key"

    # SQLAlchemy URL. Empty = SQLite file at MAIDA_DB_PATH (local/demo). Cloud:
    # postgresql+psycopg://postgres.<ref>:<password>@<pooler-host>:6543/postgres
    database_url: str = ""

    # Supabase project settings (auth mode "supabase"). The JWKS URL is derived
    # from SUPABASE_URL; SUPABASE_JWT_SECRET is only needed for projects that
    # still sign access tokens with the legacy HS256 shared secret.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    # Secret used to sign mock tokens (auth mode "mock"); never for production.
    maida_mock_jwt_secret: str = "maida-mock-secret-not-for-production"

    # Emails that get the admin role on first sign-in (comma-separated string;
    # see admin_emails below).
    maida_admin_emails: str = ""

    # Credits granted to every new account (closed beta: 10; after launch: 3).
    maida_beta_credits: int = 10

    # Upload limits and concurrency for the job pipeline.
    maida_max_pdf_mb: int = 25
    maida_max_pages: int = 80
    maida_max_running_jobs: int = 4          # whole process
    maida_max_running_jobs_per_user: int = 1
    maida_jobs_per_hour: int = 10            # per user

    # Price table used for the *estimated* cost column of llm_calls (USD per
    # million tokens). Real spend is what the provider console bills.
    llm_price_input_per_mtok: float = 3.0
    llm_price_output_per_mtok: float = 15.0

    # Serve a built frontend (frontend/build) from "/" when set: single-process
    # deployments, the Windows runner and the e2e suite use it; the compose
    # stack keeps nginx in front instead.
    maida_frontend_dir: str = ""

    @property
    def resolved_model(self) -> str:
        """Return the configured model id, if one was supplied by the researcher."""
        return self.anthropic_model

    @property
    def resolved_database_url(self) -> str:
        """SQLAlchemy URL for the study store: explicit DATABASE_URL or SQLite."""
        url = self.database_url.strip()
        if not url:
            return f"sqlite:///{self.maida_db_path}"
        # Supabase hands out "postgresql://" (or "postgres://") strings; the
        # installed driver is psycopg 3, so name it explicitly.
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def admin_emails(self) -> frozenset[str]:
        return frozenset(
            e.strip().lower() for e in self.maida_admin_emails.split(",") if e.strip()
        )

    @property
    def cloud_mode(self) -> bool:
        """True when callers are individual authenticated users (not one operator)."""
        return self.maida_auth_mode in ("supabase", "mock")

    @property
    def supabase_jwks_url(self) -> str:
        base = self.supabase_url.rstrip("/")
        return f"{base}/auth/v1/.well-known/jwks.json" if base else ""


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance, creating it on first call."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings
