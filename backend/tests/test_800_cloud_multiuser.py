"""8.0: multi-user cloud mode - identity, data isolation, credits, jobs.

Runs the real application in auth mode "mock" (locally minted bearer tokens,
same code path as Supabase tokens after verification) on a fresh SQLite file,
with a fake engine injected the way the 7.x tests do.
"""

from __future__ import annotations

import base64
import importlib
import json
import sqlite3
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from conftest import fresh_database_url, make_minimal_pdf

# ----------------------------------------------------------------------------- fixtures


def _pdf_b64(text: str = "Paper text. r = 0.30 (n = 200).") -> str:
    return base64.b64encode(make_minimal_pdf(text)).decode()


class FakeEngine:
    provider, model = "fake", "fake-model-1"

    def __init__(self, payload=None, *, raise_exc: Exception | None = None):
        self._payload = payload
        self._raise = raise_exc
        self.last_usage = None
        self.last_latency_ms = 0

    def complete(self, system, user, max_tokens=1024):
        # Mimics AnthropicEngine: usage is known for every answered call.
        self.last_latency_ms = 7
        self.last_usage = {"input_tokens": 1200, "output_tokens": 150}
        if self._raise is not None:
            raise self._raise
        return json.dumps(self._payload)  # payload None -> "null" (malformed)


GOOD = {
    "sample_n": 200, "effect_r": 0.30, "evidence_page": 2,
    "evidence_quote": "The correlation between FSTS and ROA is r = 0.30.",
    "n_evidence_page": 1, "n_evidence_quote": "The sample consists of 200 firms.",
    "doi_measure": "FSTS", "performance_measure": "ACC",
}
NO_EVIDENCE = {"sample_n": 200, "effect_r": 0.30}


@pytest.fixture()
def cloud(tmp_path, monkeypatch):
    """A mock-mode app on its own database; restores the default app after."""
    monkeypatch.setenv("MAIDA_AUTH_MODE", "mock")
    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "cloud.db"))
    url = fresh_database_url(tmp_path, "cloud")
    if not url.startswith("sqlite"):
        monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MAIDA_ADMIN_EMAILS", "operator@example.org")
    monkeypatch.setenv("MAIDA_INVITED_EMAILS", "@example.org")
    monkeypatch.setenv("MAIDA_BETA_CREDITS", "3")
    monkeypatch.setenv("MAIDA_JOBS_PER_HOUR", "4")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.delenv("MAIDA_DEMO_MODE", raising=False)

    import settings as settings_module

    settings_module._settings = None
    main = importlib.import_module("main")
    importlib.reload(main)
    client = TestClient(main.app)

    def inject(engine):
        from extractor import StatisticalExtractor

        main._get_extractor = lambda: StatisticalExtractor(engine=engine)

    def login(email, name=""):
        r = client.post("/api/auth/mock-login", json={"email": email, "name": name})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    yield main, client, inject, login

    monkeypatch.undo()
    settings_module._settings = None
    importlib.reload(main)


def extract(client, headers, inject, engine, **meta):
    inject(engine)
    return client.post("/api/extract", headers=headers,
                       json={"pdf_content": _pdf_b64(), "paper_metadata": {"title": "T", "year": 2020, **meta}})


# ----------------------------------------------------------------------------- identity


def test_health_and_config_are_public_everything_else_needs_a_token(cloud):
    main, client, _, _ = cloud
    assert client.get("/api/health").json()["auth_mode"] == "mock"
    cfg = client.get("/api/config").json()
    assert cfg["auth_mode"] == "mock" and cfg["beta_credits"] == 3
    assert client.get("/api/studies").status_code == 401
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/jobs", files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")}).status_code == 401
    assert client.get("/api/studies", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_first_sign_in_creates_the_account_with_beta_credits(cloud):
    main, client, _, login = cloud
    me = client.get("/api/me", headers=login("alice@example.org", "Alice")).json()
    assert me["email"] == "alice@example.org" and me["name"] == "Alice"
    assert me["role"] == "user" and me["credits"] == 3 and me["studies"] == 0
    # Signing in again does not grant again.
    again = client.get("/api/me", headers=login("alice@example.org")).json()
    assert again["credits"] == 3 and again["id"] == me["id"]
    ledger = client.get("/api/me/ledger", headers=login("alice@example.org")).json()
    assert [e["reason"] for e in ledger] == ["grant_beta"]


def test_admin_role_comes_from_the_email_list(cloud):
    main, client, _, login = cloud
    assert client.get("/api/me", headers=login("operator@example.org")).json()["role"] == "admin"
    assert client.get("/api/admin/users", headers=login("alice@example.org")).status_code == 403
    users = client.get("/api/admin/users", headers=login("operator@example.org")).json()
    assert {u["email"] for u in users} >= {"operator@example.org", "alice@example.org"}


def test_expired_mock_token_is_rejected(cloud):
    main, client, _, _ = cloud
    token = main._verifier.mint_mock_token("mock-x", "x@example.org", ttl_seconds=-10)
    r = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and "expired" in r.json()["detail"].lower()


# ----------------------------------------------------------------------------- isolation


def test_users_cannot_see_or_touch_each_others_studies(cloud):
    main, client, inject, login = cloud
    alice, bob = login("alice@example.org"), login("bob@example.org")

    created = extract(client, alice, inject, FakeEngine(GOOD))
    assert created.status_code == 200, created.text
    sid = created.json()["study_id"]

    assert [s["study_id"] for s in client.get("/api/studies", headers=alice).json()] == [sid]
    assert client.get("/api/studies", headers=bob).json() == []
    assert client.get(f"/api/studies/{sid}", headers=bob).status_code == 404
    patch = {"study_id": sid, "pi_approved": True, "pi_notes": "", "field_overrides": {}}
    assert client.patch(f"/api/studies/{sid}/verify", headers=bob, json=patch).status_code == 404
    assert client.post(f"/api/studies/{sid}/lock", headers=bob).status_code == 404
    assert client.delete(f"/api/studies/{sid}", headers=bob).status_code == 404
    assert client.get("/api/studies/export/csv", headers=bob).status_code == 404

    # Alice's own flow still works end to end.
    assert client.patch(f"/api/studies/{sid}/verify", headers=alice, json=patch).status_code == 200
    assert client.post(f"/api/studies/{sid}/lock", headers=alice).status_code == 200
    csv_text = client.get("/api/studies/export/csv", headers=alice).text
    assert sid in csv_text
    assert client.delete(f"/api/studies/{sid}", headers=alice).status_code == 409  # locked


def test_account_export_contains_only_the_callers_data(cloud):
    main, client, inject, login = cloud
    alice, bob = login("alice@example.org"), login("bob@example.org")
    extract(client, alice, inject, FakeEngine(GOOD))
    extract(client, bob, inject, FakeEngine(GOOD))
    dump = client.get("/api/me/export", headers=alice).json()
    assert len(dump["studies"]) == 1 and len(dump["jobs"]) == 1
    assert dump["user"]["email"] == "alice@example.org"


# ----------------------------------------------------------------------------- credits


def test_credit_rules_charge_rejected_refund_failed_block_at_zero(cloud):
    from engines import EngineError

    main, client, inject, login = cloud
    alice = login("alice@example.org")

    def balance():
        return client.get("/api/me", headers=alice).json()["credits"]

    assert balance() == 3
    assert extract(client, alice, inject, FakeEngine(GOOD)).status_code == 200
    assert balance() == 2                                           # success: charged
    r = extract(client, alice, inject, FakeEngine(NO_EVIDENCE))
    assert r.status_code == 422 and balance() == 1                  # rejected by the gate: charge kept
    r = extract(client, alice, inject, FakeEngine(raise_exc=EngineError("provider down")))
    assert r.status_code == 502 and balance() == 1                  # provider error: refunded
    r = extract(client, alice, inject, FakeEngine(None))             # "null": malformed output
    assert r.status_code == 422 and balance() == 0                  # charge kept
    r = extract(client, alice, inject, FakeEngine(GOOD))
    assert r.status_code == 402                                     # no credits left, no model call
    reasons = [e["reason"] for e in client.get("/api/me/ledger", headers=alice).json()]
    assert reasons.count("extraction") == 4 and reasons.count("refund") == 1
    assert all(e["balance_after"] >= 0 for e in client.get("/api/me/ledger", headers=alice).json())


def test_admin_can_grant_credits_and_see_usage(cloud):
    main, client, inject, login = cloud
    alice, admin = login("alice@example.org"), login("operator@example.org")
    assert extract(client, alice, inject, FakeEngine(GOOD)).status_code == 200
    r = client.post("/api/admin/credits", headers=admin, json={"email": "alice@example.org", "credits": 5})
    assert r.status_code == 200 and r.json()["credits"] == 7
    assert client.post("/api/admin/credits", headers=alice, json={"email": "alice@example.org", "credits": 5}).status_code == 403
    usage = client.get("/api/admin/usage", headers=admin).json()
    assert usage["calls"] == 1 and usage["input_tokens"] == 1200 and usage["output_tokens"] == 150
    # 1200 * 3 / 1e6 + 150 * 15 / 1e6 = 0.0036 + 0.00225
    assert usage["estimated_cost_usd"] == pytest.approx(0.00585, abs=1e-6)
    assert usage["outcomes"] == {"ok": 1}


# ----------------------------------------------------------------------------- jobs


def test_async_job_flow_reaches_a_study(cloud):
    main, client, inject, login = cloud
    alice = login("alice@example.org")
    inject(FakeEngine(GOOD))
    pdf = make_minimal_pdf("Paper. r = 0.30 (n = 200).")
    r = client.post("/api/jobs", headers=alice, files={"file": ("paper.pdf", pdf, "application/pdf")},
                    data={"title": "A paper", "year": "2019", "country": "VN"})
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["credits_charged"] == 1 and job["pages"] == 1
    # TestClient runs background tasks before returning, so the job is done.
    done = client.get(f"/api/jobs/{job['id']}", headers=alice).json()
    assert done["status"] == "succeeded" and done["study_id"] and done["model"] == "fake-model-1"
    study = client.get(f"/api/studies/{done['study_id']}", headers=alice).json()
    assert study["paper_title"] == "A paper" and study["effect_r"] == pytest.approx(0.30)
    assert client.get("/api/jobs", headers=alice).json()[0]["id"] == job["id"]
    assert client.get(f"/api/jobs/{job['id']}", headers=login("bob@example.org")).status_code == 404


def test_uploads_are_validated_before_any_charge(cloud):
    main, client, inject, login = cloud
    alice = login("alice@example.org")
    inject(FakeEngine(GOOD))
    r = client.post("/api/jobs", headers=alice, files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 400
    r = client.post("/api/jobs", headers=alice, files={"file": ("x.pdf", b"", "application/pdf")})
    assert r.status_code == 400
    assert client.get("/api/me", headers=alice).json()["credits"] == 3
    assert client.get("/api/jobs", headers=alice).json() == []


def test_hourly_rate_limit_per_user(cloud):
    main, client, inject, login = cloud
    alice = login("alice@example.org")
    admin = login("operator@example.org")
    client.post("/api/admin/credits", headers=admin, json={"email": "alice@example.org", "credits": 10})
    for _ in range(4):
        assert extract(client, alice, inject, FakeEngine(GOOD)).status_code == 200
    r = extract(client, alice, inject, FakeEngine(GOOD))
    assert r.status_code == 429 and "per hour" in r.json()["detail"]


def test_interrupted_jobs_are_failed_and_refunded_at_startup(cloud):
    from db import ExtractionJob, utcnow

    main, client, inject, login = cloud
    alice = login("alice@example.org")
    me = client.get("/api/me", headers=alice).json()
    # Simulate a job that was charged and left running by a dead process.
    with main._sessions() as s:
        s.add(ExtractionJob(id="orphan", owner_id=me["id"], status="running", credits_charged=1,
                            metadata_json={}, created_at=utcnow()))
        s.commit()
    main._credits.charge(me["id"], "orphan", 1)
    assert client.get("/api/me", headers=alice).json()["credits"] == 2
    assert main._jobs.recover_interrupted() == 1
    assert client.get("/api/jobs/orphan", headers=alice).json()["status"] == "failed"
    assert client.get("/api/me", headers=alice).json()["credits"] == 3


# ----------------------------------------------------------------------------- Supabase token verification


def _jwks_for(private_key):
    jwk = jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"kid": "k1", "use": "sig", "alg": "ES256"})
    return {"keys": [jwk]}


def test_supabase_tokens_are_verified_against_the_jwks(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import ec

    from auth import TokenVerifier
    from settings import Settings

    key = ec.generate_private_key(ec.SECP256R1())
    jwks = _jwks_for(key)
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: jwks)

    settings = Settings(maida_auth_mode="supabase", supabase_url="https://abc.supabase.co",
                        supabase_jwt_secret="legacy-secret")
    verifier = TokenVerifier(settings)
    now = int(time.time())
    good = jwt.encode({"sub": "u1", "email": "a@b.c", "aud": "authenticated", "exp": now + 60},
                      key, algorithm="ES256", headers={"kid": "k1"})
    assert verifier.verify(good)["sub"] == "u1"

    from fastapi import HTTPException

    expired = jwt.encode({"sub": "u1", "aud": "authenticated", "exp": now - 60}, key,
                         algorithm="ES256", headers={"kid": "k1"})
    with pytest.raises(HTTPException) as e:
        verifier.verify(expired)
    assert e.value.status_code == 401

    wrong_aud = jwt.encode({"sub": "u1", "aud": "anon", "exp": now + 60}, key,
                           algorithm="ES256", headers={"kid": "k1"})
    with pytest.raises(HTTPException):
        verifier.verify(wrong_aud)

    other = ec.generate_private_key(ec.SECP256R1())
    forged = jwt.encode({"sub": "u1", "aud": "authenticated", "exp": now + 60}, other,
                        algorithm="ES256", headers={"kid": "k1"})
    with pytest.raises(HTTPException):
        verifier.verify(forged)

    legacy = jwt.encode({"sub": "u2", "aud": "authenticated", "exp": now + 60}, "legacy-secret", algorithm="HS256")
    assert verifier.verify(legacy)["sub"] == "u2"
    with pytest.raises(HTTPException):
        verifier.verify(jwt.encode({"sub": "u2", "aud": "authenticated", "exp": now + 60}, "wrong", algorithm="HS256"))


# ----------------------------------------------------------------------------- migration of a 7.x file


def test_a_7x_sqlite_file_is_migrated_in_place(tmp_path):
    from models import StudyDatabaseEntry
    from store import StudyStore

    path = tmp_path / "old.db"
    old = StudyDatabaseEntry(study_id="S1", paper_title="Old", authors="A", year=2001, country="VN",
                             effect_r=0.1, sample_n=50, pi_locked=True,
                             extraction_confidence=1.0, requires_verification=False)
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE studies (study_id TEXT PRIMARY KEY, payload TEXT NOT NULL, "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now')));"
    )
    conn.execute("INSERT INTO studies (study_id, payload) VALUES (?, ?)", ("S1", old.model_dump_json()))
    conn.commit()
    conn.close()

    store = StudyStore(path)
    assert len(store) == 1
    got = store.get("S1", owner_id="local")
    assert got is not None and got.paper_title == "Old" and got.pi_locked is True
    assert store.get("S1", owner_id="someone-else") is None
    assert store.count("local", locked=True) == 1
    store.put(got)  # rewrite works on the migrated row
    assert store.get("S1").year == 2001
    store.close()


# ----------------------------------------------------------------------------- single-operator mode


def test_jobs_route_also_works_for_the_single_operator(tmp_path, monkeypatch):
    """admin_key mode (default): /api/jobs needs the shared key, counts no credits."""
    import main as app_module
    from conftest import ADMIN_HEADERS
    from extractor import StatisticalExtractor

    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "op.db"))
    app_module._studies = app_module.StudyStore(str(tmp_path / "op.db"))
    app_module._get_extractor = lambda: StatisticalExtractor(engine=FakeEngine(GOOD))
    client = TestClient(app_module.app)
    pdf = make_minimal_pdf("Paper. r = 0.30 (n = 200).")
    assert client.post("/api/jobs", files={"file": ("p.pdf", pdf, "application/pdf")}).status_code == 401
    r = client.post("/api/jobs", headers=ADMIN_HEADERS, files={"file": ("p.pdf", pdf, "application/pdf")})
    assert r.status_code == 202 and r.json()["credits_charged"] == 0
    job = client.get(f"/api/jobs/{r.json()['id']}", headers=ADMIN_HEADERS).json()
    assert job["status"] == "succeeded"
    me = client.get("/api/me", headers=ADMIN_HEADERS).json()
    assert me["id"] == "local" and me["credits"] is None and me["studies"] == 1


def test_database_url_is_normalised_for_psycopg():
    from settings import Settings

    s = Settings(database_url="postgresql://u:p@h:6543/db")
    assert s.resolved_database_url == "postgresql+psycopg://u:p@h:6543/db"
    assert Settings(database_url="postgres://u:p@h/db").resolved_database_url.startswith("postgresql+psycopg://")
    assert Settings(database_url="", maida_db_path="x.db").resolved_database_url == "sqlite:///x.db"


# ----------------------------------------------------------------------------- closed beta: invitations


def test_invitation_rules():
    from settings import Settings

    closed = Settings(maida_admin_emails="Boss@Lab.org", maida_invited_emails="")
    assert closed.is_invited("boss@lab.org") and not closed.is_invited("someone@lab.org")
    listed = Settings(maida_admin_emails="", maida_invited_emails=" A@x.org , @CTU.edu.vn ")
    assert listed.is_invited("a@X.org") and listed.is_invited("ncs@ctu.edu.vn")
    assert not listed.is_invited("b@x.org") and not listed.is_invited("ncs@student.ctu.edu.vn.evil.com")
    assert not listed.is_invited("") and not listed.is_invited("no-at-sign")
    assert Settings(maida_invited_emails="*").is_invited("anyone@anywhere.net")


def test_uninvited_sign_in_creates_nothing(cloud):
    main, client, _, login = cloud
    r = client.post("/api/auth/mock-login", json={"email": "mallory@evil.test"})
    assert r.status_code == 403 and r.json()["detail"].startswith("not_invited")
    # a token minted elsewhere (as Supabase would) is refused on every route too
    token = main._verifier.mint_mock_token("mallory-sub", "mallory@evil.test")
    for path in ("/api/me", "/api/studies", "/api/jobs"):
        assert client.get(path, headers={"Authorization": f"Bearer {token}"}).status_code == 403
    admin = login("operator@example.org")
    emails = [u["email"] for u in client.get("/api/admin/users", headers=admin).json()]
    assert "mallory@evil.test" not in emails  # no account row, so no free credits either


def test_removing_an_invitation_locks_out_an_existing_account(cloud):
    main, client, _, login = cloud
    alice, bob, admin = login("alice@example.org"), login("bob@example.org"), login("operator@example.org")
    assert client.get("/api/me", headers=alice).status_code == 200
    import settings as settings_module

    settings_module.get_settings().maida_invited_emails = "bob@example.org"
    assert client.get("/api/me", headers=alice).status_code == 403  # her still-valid token no longer works
    assert client.get("/api/me", headers=bob).status_code == 200
    assert client.get("/api/me", headers=admin).status_code == 200  # admins are always allowed
