"""
M-AIDA - FastAPI application entry point (version: see APP_VERSION below).

Routes
------
GET    /api/health                Health check (public)
GET    /api/config                Public client configuration (auth mode, Supabase URL/anon key)
POST   /api/auth/mock-login       Mint a test token (auth mode "mock" only)
GET    /api/me                    Caller's account, credit balance, counts
GET    /api/me/ledger             Caller's credit ledger
GET    /api/me/export             Everything the caller owns, as JSON
POST   /api/jobs                  Upload PDF → queued extraction job (202)
GET    /api/jobs                  Caller's jobs, newest first
GET    /api/jobs/{id}             One job (poll until succeeded/rejected/failed)
POST   /api/extract               Base64 PDF → ExtractedEffect (synchronous, 7.x)
POST   /api/extract/upload        Multipart PDF → ExtractedEffect (synchronous, 7.x)
GET    /api/studies               Caller's studies (filterable)
GET    /api/studies/{id}          Single study detail
PATCH  /api/studies/{id}/verify   PI verification + field overrides
POST   /api/studies/{id}/lock     PI permanent data lock (irreversible)
DELETE /api/studies/{id}          Delete an unlocked study
GET    /api/studies/export/csv    Export caller's locked studies as CSV
POST   /api/notion/sync           Push caller's locked studies to Notion
GET    /api/admin/users           (admin) accounts and balances
POST   /api/admin/credits         (admin) grant credits
GET    /api/admin/usage           (admin) model calls and estimated cost

Identity and data isolation (8.0)
---------------------------------
``MAIDA_AUTH_MODE`` selects how a caller is identified (see backend/auth.py):
the 7.2 shared admin key (default, single operator), Supabase JWTs (cloud,
many users) or locally minted mock tokens (tests). Every study, job and
ledger entry carries the owner's id and every route filters by it.

Data persistence
----------------
Studies, jobs, model calls, the credit ledger and the audit log live in one
SQLAlchemy database (SQLite file by default, Postgres via DATABASE_URL); see
backend/db.py and backend/store.py.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from auth import Principal, TokenVerifier, UserDirectory, build_current_user_dependency, require_admin
from credits import CreditService
from db import AuditLog, LLMCall, User, utcnow
from engines import make_engine
from extractor import PRIMARY_STAT_FIELDS, StatisticalExtractor
from jobs import JobService, machine_proposal_snapshot
from models import ExtractionRequest, StudyDatabaseEntry, VerificationDecision
from notion_sync import NotionSync
from settings import get_settings
from store import StudyStore

#: Fields a Principal Investigator may correct through PATCH /verify (7.2.0).
#: Primary statistics trigger a full re-derivation; the rest are coding
#: decisions and bibliographic metadata. Governance fields (pi_locked,
#: locked_at, study_id, machine_proposal, extraction_confidence, evidence_*)
#: and every derived quantity are deliberately absent.
PI_EDITABLE_FIELDS: frozenset[str] = frozenset({
    "effect_r", "effect_t", "effect_df", "effect_beta", "n_predictors",
    "sample_n", "sample_start", "sample_end", "p_value", "ci_lower", "ci_upper",
    "doi_measure", "performance_measure", "icrv_regime", "dpl_phase", "cdai_score",
    "country", "year", "paper_title", "authors",
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & middleware
# ---------------------------------------------------------------------------

#: Single source of the running version. /api/health, the OpenAPI document
#: and the tests read this constant; backend/pyproject.toml must match it
#: (test_721_version_consistency).
APP_VERSION = "8.0.0"

app = FastAPI(
    title=f"M-AIDA v{APP_VERSION}",
    description="Meta-Analysis Intelligent Data Assistant - I→P research pipeline",
    version=APP_VERSION,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Admin-key guard (auth mode "admin_key" only)
# ---------------------------------------------------------------------------
# In the single-operator deployment (DEPLOY.md), nginx publishes ONLY the
# frontend and proxies every /api/* request to this backend on the internal
# network - so without a check here, any site visitor could call PATCH
# /verify, POST /lock, POST /extract (burning the owner's LLM budget) or
# POST /notion/sync directly, bypassing the human-in-the-loop design the rest
# of this file exists to enforce. Mirrors the presenter-PIN guard already
# used by demo/run_defense.py: gate every mutating method behind a shared
# secret. If MAIDA_ADMIN_KEY is not set, generate one and print it once at
# startup rather than defaulting to open, so `docker compose up` still works
# for a solo operator without extra setup. In the cloud modes every route
# (not only mutations) requires a per-user bearer token instead.
_ADMIN_KEY = settings.maida_admin_key or secrets.token_urlsafe(16)
if not settings.maida_admin_key and not settings.cloud_mode:
    logger.warning(
        "MAIDA_ADMIN_KEY not set; generated a temporary admin key for this "
        "process. It will change on restart - set MAIDA_ADMIN_KEY in "
        "backend/.env for a stable key. Admin key: %s",
        _ADMIN_KEY,
    )
    print(f"Generated MAIDA admin key (unset in .env): {_ADMIN_KEY}")

_MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


@app.middleware("http")
async def admin_key_guard(request: Request, call_next):
    """Require X-MAIDA-Admin-Key on every mutating request (admin_key mode).

    Read-only routes (GET /api/studies, /api/studies/{id},
    /api/studies/export/csv, /api/health) stay public in this mode: they
    serve the published, locked dataset the project is built to make
    transparent.

    Skipped in demo mode: demo/run_defense.py wraps this same app with its
    own presenter-PIN middleware (X-MAIDA-Demo-PIN) for exactly this purpose,
    and demo mode is documented as presentation-only, never for real data
    (see MAIDA_DEMO_MODE in settings.py) - a live audience only needs the one
    PIN printed at startup, not a second secret. Skipped in the cloud modes,
    where the bearer-token dependency identifies every caller.
    """
    if settings.maida_demo_mode or settings.cloud_mode:
        return await call_next(request)
    if request.method in _MUTATING_METHODS and not secrets.compare_digest(
        request.headers.get("X-MAIDA-Admin-Key", ""), _ADMIN_KEY
    ):
        return JSONResponse({"detail": "Admin key required."}, status_code=401)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Persistent store, identity, credits, jobs
# ---------------------------------------------------------------------------
_studies = StudyStore(settings.resolved_database_url)
_sessions = _studies.session_factory
_credits = CreditService(_sessions)
_verifier = TokenVerifier(settings) if settings.cloud_mode else None
_directory = UserDirectory(_sessions, settings)
current_user = build_current_user_dependency(settings, _verifier, _directory)
CurrentUser = Annotated[Principal, Depends(current_user)]


def _get_extractor() -> StatisticalExtractor:
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured; extraction unavailable.",
        )
    engine = make_engine(
        settings.llm_provider,
        api_key=settings.anthropic_api_key,
        model=settings.resolved_model,
    )
    return StatisticalExtractor(engine=engine)


# The lambda looks `_get_extractor` up at call time, so tests can still
# monkeypatch main._get_extractor to inject a fake engine.
_jobs = JobService(settings, lambda: _studies, lambda: _get_extractor())
_jobs.recover_interrupted()


#: Kept under its 7.x name for demo/run_defense.py (seeds the P6 sample).
_machine_proposal_snapshot = machine_proposal_snapshot


def _get_notion() -> NotionSync:
    if not settings.notion_token or not settings.notion_database_id:
        raise HTTPException(
            status_code=503,
            detail="NOTION_TOKEN or NOTION_DATABASE_ID not configured.",
        )
    return NotionSync(
        token=settings.notion_token, database_id=settings.notion_database_id
    )


def _audit(owner_id: str, action: str, study_id: str | None = None, **detail: Any) -> None:
    with _sessions() as s:
        s.add(AuditLog(owner_id=owner_id, action=action, study_id=study_id,
                       detail=detail, created_at=utcnow()))
        s.commit()


# ---------------------------------------------------------------------------
# Health & public configuration
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, Any]:
    """Return service status, configuration flags and demo-readiness signals.

    The extra fields exist so the UI can show a single status strip during a
    live demo. A presenter needs to know, at a glance and before starting,
    whether the backend is up, whether the store is persistent, whether live
    extraction is actually available, and what will happen if it is not.
    """
    llm_ready = bool(settings.anthropic_api_key)
    storage = "postgres" if settings.resolved_database_url.startswith("postgres") else "sqlite"
    return {
        "status": "ok",
        "version": APP_VERSION,
        # Global count only for the single-operator deployment: in the cloud
        # modes /api/health is public and must not leak how many records all
        # accounts hold; each user sees their own counts on /api/me.
        "study_count": None if settings.cloud_mode else len(_studies),
        "anthropic_configured": llm_ready,
        "notion_configured": bool(
            settings.notion_token and settings.notion_database_id
        ),
        # Storage is persistent by construction now; reported so the UI can say so.
        "storage": storage,
        "storage_path": settings.maida_db_path if storage == "sqlite" else "",
        # The mode the next upload will actually take.
        "llm_ready": llm_ready,
        "demo_mode": settings.maida_demo_mode,
        "auth_mode": settings.maida_auth_mode,
        # No fallback mode exists: extraction is live or plainly unavailable.
        "extraction_mode": "live" if llm_ready else "unavailable",
    }


@app.get("/api/config", tags=["system"])
def client_config() -> dict[str, Any]:
    """Settings the browser needs before anyone is signed in.

    The Supabase anon/publishable key is public by design (it only grants
    what Row Level Security allows, and this backend never relies on it).
    """
    return {
        "version": APP_VERSION,
        "auth_mode": settings.maida_auth_mode,
        "supabase_url": settings.supabase_url if settings.maida_auth_mode == "supabase" else "",
        "supabase_anon_key": settings.supabase_anon_key if settings.maida_auth_mode == "supabase" else "",
        "beta_credits": settings.maida_beta_credits,
        "max_pdf_mb": settings.maida_max_pdf_mb,
        "max_pages": settings.maida_max_pages,
    }


class MockLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    name: str = ""


@app.post("/api/auth/mock-login", tags=["system"])
def mock_login(body: MockLogin) -> dict[str, Any]:
    """Mint a bearer token for tests and the e2e run (auth mode "mock" only)."""
    if settings.maida_auth_mode != "mock" or _verifier is None:
        raise HTTPException(status_code=404, detail="Not found.")
    import hashlib

    email = body.email.strip().lower()
    sub = "mock-" + hashlib.sha256(email.encode()).hexdigest()[:24]
    token = _verifier.mint_mock_token(sub, email, user_metadata={"full_name": body.name})
    principal = _directory.principal_from_claims(_verifier.verify(token))
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": principal.id, "email": principal.email, "role": principal.role, "name": principal.name}}


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


@app.get("/api/me", tags=["account"])
def me(user: CurrentUser) -> dict[str, Any]:
    with _sessions() as s:
        row = s.get(User, user.id)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "beta": bool(row.beta) if row else False,
        "credits": _credits.balance(user.id) if settings.cloud_mode else None,
        "studies": _studies.count(user.id),
        "locked": _studies.count(user.id, locked=True),
        "auth_mode": settings.maida_auth_mode,
    }


@app.get("/api/me/ledger", tags=["account"])
def my_ledger(user: CurrentUser, limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    return [{"id": e.id, "delta": e.delta, "reason": e.reason, "balance_after": e.balance_after,
             "job_id": e.ref_job_id, "note": e.note, "created_at": e.created_at}
            for e in _credits.history(user.id, limit)]


@app.get("/api/me/export", tags=["account"])
def my_export(user: CurrentUser) -> dict[str, Any]:
    """Everything the caller owns, for portability (studies, jobs, ledger)."""
    _audit(user.id, "export", kind="account")
    return {
        "exported_at": utcnow(),
        "version": APP_VERSION,
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "studies": [s.model_dump(mode="json") for s in _studies.values(user.id)],
        "jobs": [JobService.to_dict(j) for j in _jobs.list(user.id, limit=1000)],
        "ledger": [e.__dict__ for e in _credits.history(user.id, limit=1000)],
    }


# ---------------------------------------------------------------------------
# Extraction jobs (asynchronous) and the 7.x synchronous routes
# ---------------------------------------------------------------------------


def _metadata(title: str, authors: str, year: int, country: str, filename: str) -> dict[str, Any]:
    return {"title": title, "authors": authors, "year": year, "country": country, "filename": filename}


@app.post("/api/jobs", status_code=202, tags=["extraction"])
async def create_job(
    user: CurrentUser,
    background: BackgroundTasks,
    file: UploadFile,
    title: str = Form(""),
    authors: str = Form(""),
    year: int = Form(0),
    country: str = Form(""),
) -> dict[str, Any]:
    """Accept a PDF, reserve one credit and run the extraction in the background.

    Poll ``GET /api/jobs/{id}`` every couple of seconds; when ``status`` is
    ``succeeded`` the record is at ``/api/studies/{study_id}``.
    """
    pdf_bytes = await file.read()
    metadata = _metadata(title, authors, year, country, file.filename or "")
    accepted = _jobs.accept(user.id, pdf_bytes, file.filename or "", metadata)
    background.add_task(_jobs.run, accepted.id, user.id, accepted.text, metadata)
    job = _jobs.get(accepted.id, user.id)
    assert job is not None
    return JobService.to_dict(job)


@app.get("/api/jobs", tags=["extraction"])
def list_jobs(user: CurrentUser, limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
    return [JobService.to_dict(j) for j in _jobs.list(user.id, limit)]


@app.get("/api/jobs/{job_id}", tags=["extraction"])
def get_job(job_id: str, user: CurrentUser) -> dict[str, Any]:
    job = _jobs.get(job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found.")
    return JobService.to_dict(job)


def _extract_now(user: Principal, pdf_bytes: bytes, filename: str, metadata: dict[str, Any]) -> StudyDatabaseEntry:
    """Run the whole pipeline inline and answer with the 7.2 status codes."""
    accepted = _jobs.accept(user.id, pdf_bytes, filename, metadata)
    entry = _jobs.run(accepted.id, user.id, accepted.text, metadata)
    if entry is None:
        job = _jobs.get(accepted.id)
        assert job is not None
        _jobs.raise_for_job(job)
    assert entry is not None
    return entry


@app.post("/api/extract", response_model=StudyDatabaseEntry, tags=["extraction"])
def extract_pdf(request: ExtractionRequest, user: CurrentUser) -> StudyDatabaseEntry:
    """Accept a Base64-encoded PDF and return an extracted effect-size record.

    The PDF is decoded, text is extracted via pypdfium2, and the
    StatisticalExtractor LLM pipeline produces an ExtractedEffect.  The result
    is persisted in the study store and returned to the caller.

    There is NO fallback path: when live extraction is unavailable (no API
    key, no network, provider error) the error surfaces as a visible status,
    demo mode or not. A tool whose contribution is data integrity must never
    answer a real upload with an invented record (finding E1). Records whose
    statistics arrive without verbatim evidence are rejected with 422.
    """
    try:
        pdf_bytes = base64.b64decode(request.pdf_content)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid Base64 PDF content: {exc}"
        ) from exc
    metadata = dict(request.paper_metadata)
    return _extract_now(user, pdf_bytes, str(metadata.get("filename", "")), metadata)


@app.post("/api/extract/upload", response_model=StudyDatabaseEntry, tags=["extraction"])
async def extract_pdf_upload(
    user: CurrentUser,
    file: UploadFile,
    title: str = Query(""),
    authors: str = Query(""),
    year: int = Query(0),
    country: str = Query(""),
) -> StudyDatabaseEntry:
    """Multipart file upload alternative to the Base64 POST /api/extract route.

    Accepts a PDF file directly via multipart/form-data together with query
    parameters for paper metadata.
    """
    pdf_bytes = await file.read()
    metadata = _metadata(title, authors, year, country, file.filename or "")
    return _extract_now(user, pdf_bytes, file.filename or "", metadata)


# ---------------------------------------------------------------------------
# Study retrieval
# ---------------------------------------------------------------------------


@app.get("/api/studies", response_model=list[StudyDatabaseEntry], tags=["studies"])
def list_studies(
    user: CurrentUser,
    icrv: str | None = Query(None, description="Filter by icrv_regime"),
    dpl: str | None = Query(None, description="Filter by dpl_phase"),
    verified: bool | None = Query(None, description="Filter by !requires_verification"),
    locked: bool | None = Query(None, description="Filter by pi_locked"),
) -> list[StudyDatabaseEntry]:
    """Return the caller's studies with optional filtering.

    All filter parameters are ANDed together.
    """
    results = _studies.values(user.id)

    if icrv is not None:
        results = [s for s in results if s.icrv_regime == icrv]
    if dpl is not None:
        results = [s for s in results if s.dpl_phase == dpl]
    if verified is not None:
        results = [s for s in results if (not s.requires_verification) == verified]
    if locked is not None:
        results = [s for s in results if s.pi_locked == locked]

    return results


@app.get(
    "/api/studies/export/csv",
    response_class=StreamingResponse,
    tags=["studies"],
)
def export_csv(user: CurrentUser) -> StreamingResponse:
    """Stream a CSV of the caller's PI-verified and locked studies.

    Only records with ``pi_locked=True`` are included to ensure the CSV
    represents the final, quality-controlled data set used in the meta-analysis.
    """
    locked = [s for s in _studies.values(user.id) if s.pi_locked]
    if not locked:
        raise HTTPException(
            status_code=404, detail="No locked studies available for export."
        )

    buf = io.StringIO()
    # 7.2.0 (finding A4): export EVERY field of the record, in model order, so
    # the hand-off carries variance_r, variance_z, metric_type, estimand_source
    # and the evidence trail. Nested values (machine_proposal, pi_edited_fields)
    # are serialised as JSON strings.
    fieldnames = list(StudyDatabaseEntry.model_fields.keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    for study in locked:
        row = study.model_dump()
        for key, val in row.items():
            if isinstance(val, (dict, list)):
                row[key] = json.dumps(val, ensure_ascii=False, default=str)
        writer.writerow(row)

    buf.seek(0)
    _audit(user.id, "export", kind="csv", rows=len(locked))
    return StreamingResponse(
        content=iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="maida_locked_studies.csv"'
        },
    )


def _own_study(study_id: str, user: Principal) -> StudyDatabaseEntry:
    """The caller's study or 404 - never 403, so ids cannot be probed."""
    entry = _studies.get(study_id, user.id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id!r} not found.")
    return entry


@app.get("/api/studies/{study_id}", response_model=StudyDatabaseEntry, tags=["studies"])
def get_study(study_id: str, user: CurrentUser) -> StudyDatabaseEntry:
    """Return a single study by its UUID."""
    return _own_study(study_id, user)


@app.delete("/api/studies/{study_id}", status_code=204, tags=["studies"])
def delete_study(study_id: str, user: CurrentUser) -> None:
    """Delete one of the caller's studies. Locked records cannot be deleted:
    the lock is the promise that the final dataset is immutable."""
    entry = _own_study(study_id, user)
    if entry.pi_locked:
        raise HTTPException(status_code=409, detail="Locked studies cannot be deleted.")
    _studies.delete(study_id, user.id)
    _audit(user.id, "delete", study_id)


# ---------------------------------------------------------------------------
# Verification & locking
# ---------------------------------------------------------------------------


@app.patch(
    "/api/studies/{study_id}/verify",
    response_model=StudyDatabaseEntry,
    tags=["verification"],
)
def verify_study(study_id: str, decision: VerificationDecision, user: CurrentUser) -> StudyDatabaseEntry:
    """Apply PI field overrides and approval status to a study.

    Field overrides in ``decision.field_overrides`` are applied to the stored
    entry.  This route does NOT lock the record; call POST /lock to do that.

    The ``effect_r`` field will be recomputed automatically if the PI overrides
    ``effect_t``/``effect_df`` or ``effect_beta`` but not ``effect_r`` directly.
    """
    entry = _own_study(study_id, user)

    if entry.pi_locked:
        raise HTTPException(
            status_code=409,
            detail="Study is already locked; overrides are not permitted.",
        )

    # 7.2.0 (findings B1–B3): a WHITELIST of PI-editable fields. Everything
    # else (pi_locked, locked_at, study_id, machine_proposal,
    # extraction_confidence, evidence_*, every derived quantity) is rejected
    # with 422 rather than silently ignored or silently applied.
    overrides = dict(decision.field_overrides)
    rejected = sorted(k for k in overrides if k not in PI_EDITABLE_FIELDS)
    if rejected:
        raise HTTPException(
            status_code=422,
            detail=(
                "field_overrides may only touch PI-editable fields; rejected: "
                + ", ".join(rejected)
                + ". Editable: " + ", ".join(sorted(PI_EDITABLE_FIELDS))
            ),
        )
    data = entry.model_dump()
    for field, value in overrides.items():
        data[field] = value

    # Any change to a primary statistic re-derives EVERY dependent quantity
    # (r, df, variance_r, variance_z, metric_type, estimand_source,
    # source_controls, df_source, lambda_applied, r_source,
    # beta_outside_pb_domain) through the same function live extraction uses,
    # so a PI correction can never leave a stale variance or a mislabelled
    # estimand behind (findings A1–A3). Precedence follows extraction
    # (r > t > beta); a PI who supplies t/df or beta WITHOUT a new r is asking
    # for the conversion, so the previous r is dropped from the inputs.
    touched = [k for k in overrides if k in PRIMARY_STAT_FIELDS]
    # 7.2.1: a record written before 7.2.0 (an imported or demo-seeded row, or a
    # row from an older SQLite store) carries a primary statistic but no
    # variance. Derive it on the first verification so the record can pass the
    # lock gate, instead of being stuck behind a 422 forever.
    legacy = data.get("variance_r") is None and any(
        data.get(k) is not None for k in ("effect_r", "effect_t", "effect_beta"))
    if touched or legacy:
        primary = {k: data.get(k) for k in PRIMARY_STAT_FIELDS}
        if touched and "effect_r" not in overrides:
            if any(k in overrides for k in ("effect_t", "effect_df")) and \
                    data.get("effect_t") is not None:
                primary["effect_r"] = None
            elif "effect_beta" in overrides and data.get("effect_beta") is not None:
                primary["effect_r"] = None
                primary["effect_t"] = None
        derived = StatisticalExtractor.derive_from_primary(primary)
        confidence = derived.pop("confidence")  # machine score is NOT overwritten
        del confidence
        data.update(derived)
        if overrides:
            data["pi_edited_fields"] = sorted(set(data.get("pi_edited_fields") or []) | set(overrides))
            data["pi_override_at"] = datetime.now(timezone.utc)
    elif overrides:
        data["pi_edited_fields"] = sorted(set(data.get("pi_edited_fields") or []) | set(overrides))
        data["pi_override_at"] = datetime.now(timezone.utc)

    data["pi_notes"] = decision.pi_notes
    # Approval clears the flag only for a record that actually carries an
    # effect size; a record without r (beta outside the P&B domain) stays
    # flagged whatever the PI ticked (finding A3).
    if data.get("effect_r") is None:
        data["requires_verification"] = True
        data["pi_approved_at"] = None
    elif decision.pi_approved:
        data["requires_verification"] = False
        # 8.0: the approval itself is recorded; the lock gate requires it.
        data["pi_approved_at"] = datetime.now(timezone.utc)
    else:
        data["pi_approved_at"] = None

    updated = StudyDatabaseEntry(**data)
    _studies.put(updated, owner_id=user.id)
    _audit(user.id, "verify", study_id, overrides=sorted(overrides), approved=decision.pi_approved)
    return updated


@app.post(
    "/api/studies/{study_id}/lock",
    response_model=StudyDatabaseEntry,
    tags=["verification"],
)
def lock_study(study_id: str, user: CurrentUser) -> StudyDatabaseEntry:
    """Permanently lock a study record.

    This operation is IRREVERSIBLE.  Once locked:
    - The ``pi_locked`` flag is set to True.
    - ``locked_at`` is stamped with the current UTC time.
    - Subsequent calls to PATCH /verify will return 409 Conflict.

    Only records that have been PI-approved (``requires_verification=False``)
    can be locked.
    """
    entry = _own_study(study_id, user)

    if entry.pi_locked:
        return entry  # Idempotent - already locked

    if entry.requires_verification:
        raise HTTPException(
            status_code=422,
            detail=(
                "Study still requires verification; "
                "approve via PATCH /verify before locking."
            ),
        )
    if entry.pi_approved_at is None:
        # 8.0: a high machine confidence is not an approval. Nothing is locked
        # until a person has approved it through PATCH /verify.
        raise HTTPException(
            status_code=422,
            detail="Study has not been approved by the PI; approve via PATCH /verify before locking.",
        )
    if entry.effect_r is None or entry.variance_r is None:
        # 7.2.0 (finding A3): final data must carry an effect size AND its
        # sampling variance; a record without either cannot be pooled.
        raise HTTPException(
            status_code=422,
            detail="Study has no usable effect size / variance; it cannot be locked.",
        )

    data = entry.model_dump()
    data["pi_locked"] = True
    data["locked_at"] = datetime.now(timezone.utc)
    locked = StudyDatabaseEntry(**data)
    _studies.put(locked, owner_id=user.id)
    _audit(user.id, "lock", study_id)
    return locked


# ---------------------------------------------------------------------------
# Notion sync
# ---------------------------------------------------------------------------


@app.post("/api/notion/sync", tags=["notion"])
def notion_sync(user: CurrentUser) -> dict[str, Any]:
    """Push the caller's PI-locked studies to the configured Notion database.

    Returns a summary with counts of successfully synced and failed records.
    Studies that already have a ``notion_page_id`` are updated; new studies
    create a fresh Notion page.
    """
    locked = [s for s in _studies.values(user.id) if s.pi_locked]
    if not locked:
        return {"synced": 0, "failed": 0, "message": "No locked studies to sync."}

    notion = _get_notion()
    synced = 0
    failed = 0
    errors: list[str] = []

    for study in locked:
        try:
            page_id = notion.push_study(study)
            data = study.model_dump()
            data["notion_page_id"] = page_id
            _studies.put(StudyDatabaseEntry(**data), owner_id=user.id)
            synced += 1
        except Exception as exc:
            logger.error("Notion sync failed for study %s: %s", study.study_id, exc)
            errors.append(f"{study.study_id}: {exc}")
            failed += 1

    return {
        "synced": synced,
        "failed": failed,
        "errors": errors,
        "message": f"Sync complete: {synced} pushed, {failed} failed.",
    }


# ---------------------------------------------------------------------------
# Admin (operator) routes
# ---------------------------------------------------------------------------


class CreditGrant(BaseModel):
    user_id: str = ""
    email: str = ""
    credits: int = Field(..., ge=1, le=10000)
    note: str = ""


@app.get("/api/admin/users", tags=["admin"])
def admin_users(user: CurrentUser) -> list[dict[str, Any]]:
    require_admin(user)
    with _sessions() as s:
        # The "local" pseudo-user exists only for the single-operator store.
        rows = s.scalars(select(User).where(User.id != "local").order_by(User.created_at)).all()
        return [{
            "id": u.id, "email": u.email, "name": u.name, "role": u.role, "beta": u.beta,
            "credits": u.credits_balance, "created_at": u.created_at, "last_seen_at": u.last_seen_at,
            "studies": _studies.count(u.id),
        } for u in rows]


@app.post("/api/admin/credits", tags=["admin"])
def admin_grant_credits(body: CreditGrant, user: CurrentUser) -> dict[str, Any]:
    require_admin(user)
    with _sessions() as s:
        target = s.get(User, body.user_id) if body.user_id else None
        if target is None and body.email:
            target = s.scalars(select(User).where(User.email == body.email.strip().lower())).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found (they must sign in once first).")
    balance = _credits.grant(target.id, body.credits, reason="adjust_admin",
                             note=body.note or f"granted by {user.email or user.id}")
    _audit(user.id, "grant", target=target.id, credits=body.credits)
    return {"user_id": target.id, "email": target.email, "credits": balance}


@app.get("/api/admin/usage", tags=["admin"])
def admin_usage(user: CurrentUser, days: int = Query(30, ge=1, le=365)) -> dict[str, Any]:
    require_admin(user)
    from datetime import timedelta

    since = utcnow() - timedelta(days=days)
    with _sessions() as s:
        totals = s.execute(
            select(func.count(LLMCall.id), func.coalesce(func.sum(LLMCall.input_tokens), 0),
                   func.coalesce(func.sum(LLMCall.output_tokens), 0), func.coalesce(func.sum(LLMCall.cost_usd), 0.0))
            .where(LLMCall.created_at >= since)
        ).one()
        per_user = s.execute(
            select(LLMCall.owner_id, func.count(LLMCall.id), func.coalesce(func.sum(LLMCall.cost_usd), 0.0))
            .where(LLMCall.created_at >= since).group_by(LLMCall.owner_id)
        ).all()
        outcomes = s.execute(
            select(LLMCall.outcome, func.count(LLMCall.id)).where(LLMCall.created_at >= since)
            .group_by(LLMCall.outcome)
        ).all()
    return {
        "days": days,
        "calls": int(totals[0]), "input_tokens": int(totals[1]), "output_tokens": int(totals[2]),
        "estimated_cost_usd": round(float(totals[3]), 6),
        "per_user": [{"user_id": r[0], "calls": int(r[1]), "estimated_cost_usd": round(float(r[2]), 6)} for r in per_user],
        "outcomes": {r[0]: int(r[1]) for r in outcomes},
        "price_table": {"input_per_mtok": settings.llm_price_input_per_mtok,
                        "output_per_mtok": settings.llm_price_output_per_mtok},
    }


# ---------------------------------------------------------------------------
# Optional: serve the built frontend from this process
# ---------------------------------------------------------------------------

if settings.maida_frontend_dir:
    _front = Path(settings.maida_frontend_dir)
    if (_front / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=_front / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):  # pragma: no cover - exercised by the e2e run
            candidate = (_front / path).resolve()
            if path and candidate.is_file() and str(candidate).startswith(str(_front.resolve())):
                return FileResponse(candidate)
            return FileResponse(_front / "index.html")
    else:
        logger.warning("MAIDA_FRONTEND_DIR=%s has no index.html; not serving a frontend", _front)


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.maida_port,
        reload=True,
    )
