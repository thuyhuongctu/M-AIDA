"""
M-AIDA - FastAPI application entry point (version: see APP_VERSION below).

Routes
------
POST   /api/extract               Upload PDF → ExtractedEffect
GET    /api/studies               List all studies (filterable)
GET    /api/studies/{id}          Single study detail
PATCH  /api/studies/{id}/verify   PI verification + field overrides
POST   /api/studies/{id}/lock     PI permanent data lock (irreversible)
GET    /api/studies/export/csv    Export verified+locked studies as CSV
GET    /api/health                Health check
POST   /api/notion/sync           Push all locked studies to Notion

Data persistence
----------------
Studies are persisted in SQLite via ``store.StudyStore`` (see backend/store.py),
keyed by study_id (UUID string).  Records therefore survive process restarts,
which matters most in a live demo: a reload in front of an audience no longer
erases verified and locked work.
"""

from __future__ import annotations

import base64
import csv
import io
import logging
import json
from datetime import datetime, timezone
from typing import Any

import fitz  # PyMuPDF
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from engines import make_engine
from extractor import (
    PRIMARY_STAT_FIELDS,
    EvidenceMissingError,
    MalformedLLMOutputError,
    StatisticalExtractor,
)
from models import ExtractedEffect, ExtractionRequest, StudyDatabaseEntry, VerificationDecision
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
APP_VERSION = "7.2.1"

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
# Persistent study store (SQLite; see backend/store.py)
# ---------------------------------------------------------------------------
_studies = StudyStore(settings.maida_db_path)


# ---------------------------------------------------------------------------
# Lazy-initialised service singletons
# ---------------------------------------------------------------------------


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


def _get_notion() -> NotionSync:
    if not settings.notion_token or not settings.notion_database_id:
        raise HTTPException(
            status_code=503,
            detail="NOTION_TOKEN or NOTION_DATABASE_ID not configured.",
        )
    return NotionSync(
        token=settings.notion_token, database_id=settings.notion_database_id
    )


# ---------------------------------------------------------------------------
# Health check
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
    return {
        "status": "ok",
        "version": APP_VERSION,
        "study_count": len(_studies),
        "anthropic_configured": llm_ready,
        "notion_configured": bool(
            settings.notion_token and settings.notion_database_id
        ),
        # Storage is persistent by construction now; reported so the UI can say so.
        "storage": "sqlite",
        "storage_path": settings.maida_db_path,
        # The mode the next upload will actually take.
        "llm_ready": llm_ready,
        "demo_mode": settings.maida_demo_mode,
        # No fallback mode exists: extraction is live or plainly unavailable.
        "extraction_mode": "live" if llm_ready else "unavailable",
    }


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _machine_proposal_snapshot(effect) -> dict:
    """Freeze what the model proposed before any human touches the record."""
    keep = (
        "effect_r", "effect_t", "effect_beta", "effect_df", "sample_n",
        "p_value", "ci_lower", "ci_upper", "doi_measure",
        "performance_measure", "extraction_confidence", "df_imputed",
        "beta_outside_pb_domain",
    )
    dump = effect.model_dump()
    return {k: dump.get(k) for k in keep}


@app.post("/api/extract", response_model=StudyDatabaseEntry, tags=["extraction"])
def extract_pdf(request: ExtractionRequest) -> StudyDatabaseEntry:
    """Accept a Base64-encoded PDF and return an extracted effect-size record.

    The PDF is decoded, text is extracted via PyMuPDF, and the
    StatisticalExtractor LLM pipeline produces an ExtractedEffect.  The result
    is persisted in the study store and returned to the caller.

    There is NO fallback path: when live extraction is unavailable (no API
    key, no network, provider error) the error surfaces as a visible status,
    demo mode or not. A tool whose contribution is data integrity must never
    answer a real upload with an invented record (finding E1). Records whose
    statistics arrive without verbatim evidence are rejected with 422.
    """
    # Decode PDF bytes
    try:
        pdf_bytes = base64.b64decode(request.pdf_content)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid Base64 PDF content: {exc}"
        ) from exc

    # Extract plain text with PyMuPDF
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: list[str] = [page.get_text() for page in doc]  # type: ignore[union-attr]
        full_text = "\n".join(pages_text)
        doc.close()
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF text extraction failed: {exc}"
        ) from exc

    try:
        extractor = _get_extractor()
        effect: ExtractedEffect = extractor.extract_from_text(
            full_text, request.paper_metadata
        )
    except EvidenceMissingError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Extraction rejected: the model proposed statistics without "
                f"verbatim evidence from the paper ({exc}). No record was created."
            ),
        ) from exc
    except MalformedLLMOutputError as exc:
        # C1 (7.2.0): untrusted model output that is not a well-typed JSON
        # object is a visible 422, never a 500 and never an empty record.
        raise HTTPException(
            status_code=422,
            detail=f"Extraction rejected: malformed model output ({exc}). No record was created.",
        ) from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    entry = StudyDatabaseEntry(**effect.model_dump())
    entry.machine_proposal = _machine_proposal_snapshot(effect)
    _studies.put(entry)
    return entry


@app.post("/api/extract/upload", response_model=StudyDatabaseEntry, tags=["extraction"])
async def extract_pdf_upload(
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
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    encoded = base64.b64encode(pdf_bytes).decode()
    metadata = {
        "title": title,
        "authors": authors,
        "year": year,
        "country": country,
        "filename": file.filename or "",
    }

    req = ExtractionRequest(pdf_content=encoded, paper_metadata=metadata)
    return extract_pdf(req)


# ---------------------------------------------------------------------------
# Study retrieval
# ---------------------------------------------------------------------------


@app.get("/api/studies", response_model=list[StudyDatabaseEntry], tags=["studies"])
def list_studies(
    icrv: str | None = Query(None, description="Filter by icrv_regime"),
    dpl: str | None = Query(None, description="Filter by dpl_phase"),
    verified: bool | None = Query(None, description="Filter by !requires_verification"),
    locked: bool | None = Query(None, description="Filter by pi_locked"),
) -> list[StudyDatabaseEntry]:
    """Return all studies with optional filtering.

    All filter parameters are ANDed together.
    """
    results = _studies.values()

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
def export_csv() -> StreamingResponse:
    """Stream a CSV of all PI-verified and locked studies.

    Only records with ``pi_locked=True`` are included to ensure the CSV
    represents the final, quality-controlled data set used in the meta-analysis.
    """
    locked = [s for s in _studies.values() if s.pi_locked]
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
    return StreamingResponse(
        content=iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="maida_locked_studies.csv"'
        },
    )


@app.get("/api/studies/{study_id}", response_model=StudyDatabaseEntry, tags=["studies"])
def get_study(study_id: str) -> StudyDatabaseEntry:
    """Return a single study by its UUID."""
    entry = _studies.get(study_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id!r} not found.")
    return entry


# ---------------------------------------------------------------------------
# Verification & locking
# ---------------------------------------------------------------------------


@app.patch(
    "/api/studies/{study_id}/verify",
    response_model=StudyDatabaseEntry,
    tags=["verification"],
)
def verify_study(study_id: str, decision: VerificationDecision) -> StudyDatabaseEntry:
    """Apply PI field overrides and approval status to a study.

    Field overrides in ``decision.field_overrides`` are applied to the stored
    entry.  This route does NOT lock the record; call POST /lock to do that.

    The ``effect_r`` field will be recomputed automatically if the PI overrides
    ``effect_t``/``effect_df`` or ``effect_beta`` but not ``effect_r`` directly.
    """
    entry = _studies.get(study_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id!r} not found.")

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
    if touched:
        primary = {k: data.get(k) for k in PRIMARY_STAT_FIELDS}
        if "effect_r" not in overrides:
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
    elif decision.pi_approved:
        data["requires_verification"] = False

    updated = StudyDatabaseEntry(**data)
    _studies.put(updated)
    return updated


@app.post(
    "/api/studies/{study_id}/lock",
    response_model=StudyDatabaseEntry,
    tags=["verification"],
)
def lock_study(study_id: str) -> StudyDatabaseEntry:
    """Permanently lock a study record.

    This operation is IRREVERSIBLE.  Once locked:
    - The ``pi_locked`` flag is set to True.
    - ``locked_at`` is stamped with the current UTC time.
    - Subsequent calls to PATCH /verify will return 409 Conflict.

    Only records that have been PI-approved (``requires_verification=False``)
    can be locked.
    """
    entry = _studies.get(study_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id!r} not found.")

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
    _studies.put(locked)
    return locked


# ---------------------------------------------------------------------------
# Notion sync
# ---------------------------------------------------------------------------


@app.post("/api/notion/sync", tags=["notion"])
def notion_sync() -> dict[str, Any]:
    """Push all PI-locked studies to the configured Notion database.

    Returns a summary with counts of successfully synced and failed records.
    Studies that already have a ``notion_page_id`` are updated; new studies
    create a fresh Notion page.
    """
    locked = [s for s in _studies.values() if s.pi_locked]
    if not locked:
        return {"synced": 0, "failed": 0, "message": "No locked studies to sync."}

    notion = _get_notion()
    synced = 0
    failed = 0
    errors: list[str] = []

    for study in locked:
        try:
            page_id = notion.push_study(study)
            # Persist the Notion page_id back to the in-memory store
            data = study.model_dump()
            data["notion_page_id"] = page_id
            _studies.put(StudyDatabaseEntry(**data))
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
