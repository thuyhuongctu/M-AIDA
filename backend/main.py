"""
M-AIDA v7.0 - FastAPI application entry point.

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
Studies are stored in an in-memory dict keyed by study_id (UUID string).
TODO: Replace with SQLite persistence using aiosqlite + SQLAlchemy Core so
      data survives process restarts.  The StudyDatabaseEntry model already
      has all required fields; only main.py needs to change.
"""

from __future__ import annotations

import base64
import csv
import io
import logging
from datetime import datetime
from typing import Any

import fitz  # PyMuPDF
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from engines import make_engine
from extractor import StatisticalExtractor
from models import ExtractedEffect, ExtractionRequest, StudyDatabaseEntry, VerificationDecision
from notion_sync import NotionSync
from settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & middleware
# ---------------------------------------------------------------------------

app = FastAPI(
    title="M-AIDA v7.0",
    description="Meta-Analysis Intelligent Data Assistant - I→P research pipeline",
    version="7.0.0",
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
# In-memory study store
# TODO: Replace with SQLite persistence (aiosqlite + SQLAlchemy Core)
# ---------------------------------------------------------------------------
_studies: dict[str, StudyDatabaseEntry] = {}


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
    """Return service status and configuration flags."""
    return {
        "status": "ok",
        "version": "7.0.0",
        "study_count": len(_studies),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "notion_configured": bool(
            settings.notion_token and settings.notion_database_id
        ),
    }


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


@app.post("/api/extract", response_model=StudyDatabaseEntry, tags=["extraction"])
def extract_pdf(request: ExtractionRequest) -> StudyDatabaseEntry:
    """Accept a Base64-encoded PDF and return an extracted effect-size record.

    The PDF is decoded, text is extracted via PyMuPDF, and the
    StatisticalExtractor LLM pipeline produces an ExtractedEffect.  The result
    is stored in the in-memory study store and returned to the caller.
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

    extractor = _get_extractor()
    try:
        effect: ExtractedEffect = extractor.extract_from_text(
            full_text, request.paper_metadata
        )
    except Exception as exc:
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    entry = StudyDatabaseEntry(**effect.model_dump())
    _studies[entry.study_id] = entry
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
    results = list(_studies.values())

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
    # Field order is chosen to match the dissertation data matrix convention
    fieldnames = [
        "study_id",
        "paper_title",
        "authors",
        "year",
        "country",
        "sample_n",
        "sample_start",
        "sample_end",
        "effect_r",
        "effect_t",
        "effect_beta",
        "effect_df",
        "p_value",
        "ci_lower",
        "ci_upper",
        "doi_measure",
        "performance_measure",
        "icrv_regime",
        "dpl_phase",
        "cdai_score",
        "extraction_confidence",
        "pi_notes",
        "locked_at",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for study in locked:
        writer.writerow(study.model_dump())

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

    # Apply overrides to a mutable copy
    overrides = decision.field_overrides
    data = entry.model_dump()
    for field, value in overrides.items():
        if field in data:
            data[field] = value
        else:
            logger.warning("Ignoring unknown field override %r", field)

    # Recompute the canonical Pearson r when the PI corrects an upstream
    # statistic (t/df or β) but does not override effect_r directly, so the
    # meta-analysis never uses a stale correlation. An explicit effect_r
    # override always wins.
    data["effect_r"] = StatisticalExtractor.resolve_overridden_r(data, overrides)

    data["pi_notes"] = decision.pi_notes
    # Approval clears the requires_verification flag
    if decision.pi_approved:
        data["requires_verification"] = False

    updated = StudyDatabaseEntry(**data)
    _studies[study_id] = updated
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

    data = entry.model_dump()
    data["pi_locked"] = True
    data["locked_at"] = datetime.utcnow()
    locked = StudyDatabaseEntry(**data)
    _studies[study_id] = locked
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
            _studies[study.study_id] = StudyDatabaseEntry(**data)
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
