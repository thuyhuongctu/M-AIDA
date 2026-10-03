"""
Caller identity for M-AIDA 8.x.

Three modes, chosen by ``MAIDA_AUTH_MODE`` (settings.py):

admin_key
    The 7.2 behaviour: one operator, one shared secret on mutating requests
    (``X-MAIDA-Admin-Key``, checked by the middleware in main.py). Every
    record belongs to the pseudo-user ``local`` and credits are not counted.

supabase
    Multi-user cloud. The frontend signs in with Supabase Auth and sends
    ``Authorization: Bearer <access token>`` on every request. The backend
    verifies the token locally - signature against the project's JWKS
    (ES256/RS256) or, for projects still on the legacy shared secret, HS256
    with ``SUPABASE_JWT_SECRET`` - then takes ``sub`` as the user id. No call
    to Supabase per request; the JWKS is cached by PyJWT.

mock
    Same request shape as ``supabase`` but tokens are minted by
    ``POST /api/auth/mock-login`` with a local HS256 secret. Exists so the
    test-suite and the Playwright e2e run can exercise the real multi-user
    code path without a Supabase project. Refused at startup in production
    builds unless explicitly enabled (see main.py).

The first request of an unknown ``sub`` creates the ``users`` row and grants
the beta credits; admins are recognised by e-mail (``MAIDA_ADMIN_EMAILS``).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import sessionmaker

from db import LOCAL_OWNER_ID, User, utcnow
from settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller as seen by route handlers."""

    id: str
    email: str
    role: str  # "user" | "admin"
    name: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


LOCAL_PRINCIPAL = Principal(id=LOCAL_OWNER_ID, email="", role="admin", name="Local operator")


class TokenVerifier:
    """Verifies bearer tokens for the configured mode and returns their claims."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mode = settings.maida_auth_mode
        self._jwks_client: jwt.PyJWKClient | None = None
        self._lock = threading.Lock()
        if self.mode == "supabase" and not settings.supabase_url and not settings.supabase_jwt_secret:
            raise RuntimeError(
                "MAIDA_AUTH_MODE=supabase needs SUPABASE_URL (for the JWKS) or SUPABASE_JWT_SECRET."
            )

    # -- token minting (mock mode only) -------------------------------------

    def mint_mock_token(self, sub: str, email: str, ttl_seconds: int = 3600, **extra) -> str:
        if self.mode != "mock":
            raise RuntimeError("mock tokens can only be minted in auth mode 'mock'")
        now = int(time.time())
        claims = {
            "sub": sub,
            "email": email,
            "aud": self.settings.supabase_jwt_audience,
            "role": "authenticated",
            "iat": now,
            "exp": now + ttl_seconds,
            **extra,
        }
        return jwt.encode(claims, self.settings.maida_mock_jwt_secret, algorithm="HS256")

    # -- verification ---------------------------------------------------------

    def _jwks(self) -> jwt.PyJWKClient:
        with self._lock:
            if self._jwks_client is None:
                self._jwks_client = jwt.PyJWKClient(
                    self.settings.supabase_jwks_url, cache_keys=True, lifespan=3600
                )
            return self._jwks_client

    def verify(self, token: str) -> dict:
        audience = self.settings.supabase_jwt_audience
        options = {"require": ["sub", "exp"]}
        try:
            if self.mode == "mock":
                return jwt.decode(
                    token, self.settings.maida_mock_jwt_secret,
                    algorithms=["HS256"], audience=audience, options=options,
                )
            header = jwt.get_unverified_header(token)
            alg = header.get("alg", "")
            if alg == "HS256":
                if not self.settings.supabase_jwt_secret:
                    raise HTTPException(401, "Token uses HS256 but SUPABASE_JWT_SECRET is not configured.")
                return jwt.decode(
                    token, self.settings.supabase_jwt_secret,
                    algorithms=["HS256"], audience=audience, options=options,
                )
            if alg not in ("ES256", "RS256"):
                raise HTTPException(401, f"Unsupported token algorithm {alg!r}.")
            if not self.settings.supabase_jwks_url:
                raise HTTPException(401, "SUPABASE_URL is not configured; cannot fetch JWKS.")
            signing_key = self._jwks().get_signing_key_from_jwt(token)
            return jwt.decode(
                token, signing_key.key, algorithms=[alg], audience=audience, options=options,
            )
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(401, "Session expired; please sign in again.") from exc
        except jwt.InvalidAudienceError as exc:
            raise HTTPException(401, "Token audience mismatch.") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(401, f"Invalid token: {exc}") from exc


class UserDirectory:
    """users table access: create-on-first-sight, role assignment, beta grant."""

    def __init__(self, session_factory: sessionmaker, settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    def principal_from_claims(self, claims: dict) -> Principal:
        from credits import CreditService  # local import: credits imports db only

        sub = str(claims["sub"])
        email = str(claims.get("email") or "").lower()
        # Closed beta: refuse before anything is written, so an uninvited
        # sign-in creates no account and no free credits. Checked on every
        # request, so removing an address from the list also locks out an
        # account that already exists (its records stay in the database).
        if not self.settings.is_invited(email):
            logger.info("Refused sign-in for %s: not on MAIDA_INVITED_EMAILS", email or "(no e-mail)")
            raise HTTPException(
                status_code=403,
                detail="not_invited: this e-mail address is not on the M-AIDA closed-beta list.",
            )
        meta = claims.get("user_metadata") or {}
        name = str(meta.get("full_name") or meta.get("name") or "")
        wants_admin = bool(email) and email in self.settings.admin_emails
        with self.session_factory() as s:
            user = s.get(User, sub)
            created = user is None
            if created:
                user = User(
                    id=sub, email=email, name=name,
                    role="admin" if wants_admin else "user",
                    beta=True, credits_balance=0, created_at=utcnow(),
                )
                s.add(user)
            else:
                if email and user.email != email:
                    user.email = email
                if name and user.name != name:
                    user.name = name
                if wants_admin and user.role != "admin":
                    user.role = "admin"
            user.last_seen_at = utcnow()
            s.commit()
            principal = Principal(id=user.id, email=user.email, role=user.role, name=user.name)
        if created and self.settings.maida_beta_credits > 0:
            CreditService(self.session_factory).grant(
                principal.id, self.settings.maida_beta_credits, reason="grant_beta",
                note="Closed-beta starting balance",
            )
            logger.info("New account %s (%s): granted %d beta credits",
                        principal.id, principal.email, self.settings.maida_beta_credits)
        return principal

    def get(self, user_id: str) -> User | None:
        with self.session_factory() as s:
            return s.get(User, user_id)


def build_current_user_dependency(settings: Settings, verifier: TokenVerifier | None,
                                  directory: UserDirectory):
    """Return a FastAPI dependency resolving the caller for the configured mode."""

    def current_user(request: Request) -> Principal:
        if not settings.cloud_mode:
            # admin_key / demo: the shared-secret middleware already ran.
            return LOCAL_PRINCIPAL
        assert verifier is not None
        header = request.headers.get("Authorization", "")
        if not header.lower().startswith("bearer "):
            raise HTTPException(401, "Sign-in required (missing bearer token).")
        claims = verifier.verify(header[7:].strip())
        return directory.principal_from_claims(claims)

    return current_user


def require_admin(principal: Principal) -> Principal:
    if not principal.is_admin:
        raise HTTPException(403, "Admin role required.")
    return principal


__all__ = [
    "Principal", "LOCAL_PRINCIPAL", "TokenVerifier", "UserDirectory",
    "build_current_user_dependency", "require_admin", "Depends",
]
