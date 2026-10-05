"""8.0: sign-in method for the internal trial (MAIDA_LOGIN_METHOD).

"password" = e-mail + password of accounts the operator creates by hand in
Supabase (no e-mail is sent, so no SMTP is needed). The browser learns the
method from /api/config; the backend still verifies every Supabase token and
still applies the invitation list, whatever the method.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_with(tmp_path, monkeypatch):
    made = []

    def build(**env):
        monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / f"lm{len(made)}.db"))
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("MAIDA_LOGIN_METHOD", raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        import settings as settings_module

        settings_module._settings = None
        main = importlib.import_module("main")
        importlib.reload(main)
        made.append(main)
        return TestClient(main.app)

    yield build

    monkeypatch.undo()
    import settings as settings_module

    settings_module._settings = None
    importlib.reload(importlib.import_module("main"))


SUPA = {
    "MAIDA_AUTH_MODE": "supabase",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "sb_publishable_test",
    "SUPABASE_JWT_SECRET": "x" * 40,
}


def test_password_method_is_announced_to_the_browser(app_with):
    cfg = app_with(**SUPA, MAIDA_LOGIN_METHOD="password").get("/api/config").json()
    assert cfg["auth_mode"] == "supabase"
    assert cfg["login_method"] == "password"
    assert cfg["supabase_url"] == "https://example.supabase.co"


def test_default_and_unknown_methods_fall_back_to_magic_link(app_with):
    assert app_with(**SUPA).get("/api/config").json()["login_method"] == "magic"
    assert app_with(**SUPA, MAIDA_LOGIN_METHOD="Telepathy").get("/api/config").json()["login_method"] == "magic"


def test_method_is_empty_outside_supabase_mode(app_with):
    cfg = app_with(MAIDA_AUTH_MODE="admin_key", MAIDA_LOGIN_METHOD="password").get("/api/config").json()
    assert cfg["login_method"] == ""


def test_password_mode_does_not_open_the_mock_sign_in_or_unauthenticated_routes(app_with):
    client = app_with(**SUPA, MAIDA_LOGIN_METHOD="password")
    assert client.post("/api/auth/mock-login", json={"email": "a@example.org"}).status_code == 404
    assert client.get("/api/studies").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_concurrent_first_requests_create_one_account_and_grant_once(app_with, monkeypatch):
    """Right after sign-in the browser sends several requests at once. A request that
    loses the race to insert the new user row must reuse that row, not fail with a
    500 and not grant the beta credits a second time."""
    from sqlalchemy.orm import Session

    app_with(**SUPA, MAIDA_LOGIN_METHOD="password", MAIDA_INVITED_EMAILS="alice@example.org",
             MAIDA_BETA_CREDITS="10")
    main = importlib.import_module("main")
    directory = main._directory
    claims = {"sub": "11111111-2222-4333-8444-555555555555", "email": "alice@example.org",
              "user_metadata": {"full_name": "Alice"}}
    first = directory.principal_from_claims(claims)

    # Replay the losing request: it looked before the winner committed, so it sees no row.
    real_get = Session.get
    calls = {"n": 0}

    def stale_once(self, entity, ident, *a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real_get(self, entity, ident, *a, **k)

    monkeypatch.setattr(Session, "get", stale_once)
    again = directory.principal_from_claims(claims)
    monkeypatch.setattr(Session, "get", real_get)

    assert again.id == first.id and again.email == "alice@example.org"
    with directory.session_factory() as s:
        from db import CreditLedger, User

        user = s.get(User, first.id)
        assert user.credits_balance == 10
        grants = s.query(CreditLedger).filter_by(owner_id=first.id, reason="grant_beta").count()
        assert grants == 1


# ----------------------------------------------------------- check_noi_bo.py (internal-trial preflight)


def _jwt(role: str) -> str:
    import base64
    import json as _json

    seg = lambda d: base64.urlsafe_b64encode(_json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    return f"{seg({'alg': 'HS256'})}.{seg({'role': role})}.sig"


def test_preflight_refuses_secret_keys_that_would_reach_every_browser():
    from check_noi_bo import key_problem

    assert key_problem("sb_publishable_abc") == ""
    assert key_problem(_jwt("anon")) == ""
    assert "BI MAT" in key_problem("sb_secret_abc")
    assert "service_role" in key_problem(_jwt("service_role"))
    assert key_problem("") and key_problem("random-string")


def test_preflight_refuses_an_open_invitation_list_and_payments():
    from check_noi_bo import BAD, OK, invite_problem, run

    assert invite_problem("*", "op@x.org")
    assert invite_problem("a@x.org", "")
    assert invite_problem("a@x.org, b@y.org", "op@x.org") == ""
    good = {"MAIDA_AUTH_MODE": "supabase", "MAIDA_LOGIN_METHOD": "password",
            "SUPABASE_URL": "https://cdpsggkiiovciqsdavka.supabase.co",
            "SUPABASE_ANON_KEY": "sb_publishable_abc", "MAIDA_INVITED_EMAILS": "a@x.org",
            "MAIDA_ADMIN_EMAILS": "op@x.org", "MAIDA_PAYMENTS": ""}
    assert all(level == OK for level, _ in run(good, fetch_jwks=False))
    for change in ({"MAIDA_LOGIN_METHOD": "magic"}, {"MAIDA_PAYMENTS": "payos"},
                   {"SUPABASE_URL": "http://localhost"}, {"MAIDA_INVITED_EMAILS": "*"}):
        assert any(level == BAD for level, _ in run({**good, **change}, fetch_jwks=False)), change
    # Every printed line is ASCII: the old Windows console cannot show Vietnamese diacritics.
    for env in (good, {**good, "MAIDA_INVITED_EMAILS": "*", "SUPABASE_ANON_KEY": "sb_secret_x"}):
        for _, msg in run(env, fetch_jwks=False):
            msg.encode("ascii")
