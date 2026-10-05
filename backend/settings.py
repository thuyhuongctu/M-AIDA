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

    # Sampling temperature sent to the model. Unset = provider default (the
    # behaviour of every release up to 8.0). Set it (e.g. 0) to freeze a
    # validation configuration; validation/run_benchmark.py records it.
    llm_temperature: float | None = None

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

    # How people sign in when MAIDA_AUTH_MODE=supabase:
    #   magic    - e-mailed sign-in link (or Google); needs working SMTP on the
    #              Supabase project (the built-in mailer only reaches project
    #              members). Default: the public beta.
    #   password - e-mail + password of an account the operator created by hand
    #              in Supabase (Authentication -> Users -> Add user, "Auto
    #              Confirm"). No mail is sent, so no SMTP is needed: meant for
    #              a small internal trial with sign-ups switched off.
    maida_login_method: str = "magic"

    # Secret used to sign mock tokens (auth mode "mock"); never for production.
    maida_mock_jwt_secret: str = "maida-mock-secret-not-for-production"

    # Emails that get the admin role on first sign-in (comma-separated string;
    # see admin_emails below).
    maida_admin_emails: str = ""

    # Closed beta: who may sign in at all (auth modes "supabase" and "mock").
    # Comma-separated e-mail addresses and/or whole domains written with a
    # leading "@" (e.g. "a@x.org, @ctu.edu.vn"). "*" lets anyone with the link
    # in. Admin e-mails are always allowed. Empty = only the admins: a closed
    # beta stays closed until someone is invited, and nobody can create
    # accounts (each with free credits paid by the operator's API key) just by
    # finding the URL.
    maida_invited_emails: str = ""

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
    # Defaults = Claude Sonnet 5 / Sonnet 5.5 list price checked 03/10/2026
    # (2 USD input, 10 USD output per million tokens); earlier releases used
    # 3/15, which overstated the estimate by about half.
    llm_price_input_per_mtok: float = 2.0
    llm_price_output_per_mtok: float = 10.0

    # ------------------------------------------------------------------
    # Payments (credit packs). Off unless MAIDA_PAYMENTS is set.
    # ------------------------------------------------------------------
    #   ""     - no shop: credits come only from beta grants and the operator.
    #   payos  - payOS (VietQR) payment links; needs the three PAYOS_* keys of
    #            a payment channel and MAIDA_PUBLIC_URL for the return pages.
    #   mock   - a local fake checkout for tests and the e2e run. Refused in
    #            auth mode "supabase": anyone could pay themselves credits.
    maida_payments: str = ""
    payos_client_id: str = ""
    payos_api_key: str = ""
    payos_checksum_key: str = ""
    payos_api_base: str = "https://api-merchant.payos.vn"

    # Public address of the site (no trailing slash), used to build the
    # return and cancel URLs that the payment page sends the buyer back to.
    maida_public_url: str = ""

    # Credit packs on sale: "id:credits:price_vnd" entries separated by commas.
    # The defaults are the DRAFT prices of the 03/10/2026 commercial plan
    # (still to be approved by the co-owners); set the variable to change them.
    maida_credit_packs: str = "thu:30:149000,tongquan:100:399000,nhom:300:990000"

    # Minutes before an unpaid payment link expires.
    maida_order_ttl_minutes: int = 30

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
    def invitations(self) -> tuple[bool, frozenset[str], frozenset[str]]:
        """(open to anyone, invited addresses, invited domains)."""
        items = [i.strip().lower() for i in self.maida_invited_emails.split(",") if i.strip()]
        domains = frozenset(i[1:] for i in items if i.startswith("@") and len(i) > 1)
        addresses = frozenset(i for i in items if "@" in i and not i.startswith("@"))
        return ("*" in items, addresses, domains)

    def is_invited(self, email: str) -> bool:
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            return False
        open_to_all, addresses, domains = self.invitations
        if open_to_all or email in self.admin_emails or email in addresses:
            return True
        return email.rsplit("@", 1)[1] in domains

    @property
    def credit_packs(self) -> tuple[tuple[str, int, int], ...]:
        """(pack id, credits, price in VND) parsed from MAIDA_CREDIT_PACKS."""
        packs: list[tuple[str, int, int]] = []
        for item in self.maida_credit_packs.split(","):
            item = item.strip()
            if not item:
                continue
            parts = [p.strip() for p in item.split(":")]
            if len(parts) != 3 or not parts[0]:
                raise ValueError(f"MAIDA_CREDIT_PACKS entry {item!r} is not id:credits:price_vnd")
            pack_id, credits, price = parts[0], int(parts[1]), int(parts[2])
            if credits <= 0 or price <= 0:
                raise ValueError(f"MAIDA_CREDIT_PACKS entry {item!r} needs positive numbers")
            if any(p[0] == pack_id for p in packs):
                raise ValueError(f"MAIDA_CREDIT_PACKS has pack id {pack_id!r} twice")
            packs.append((pack_id, credits, price))
        return tuple(packs)

    @property
    def payments_provider(self) -> str:
        """"" (no shop), "payos" or "mock"."""
        return self.maida_payments.strip().lower()

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
