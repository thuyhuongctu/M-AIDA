"""
Extraction job pipeline for M-AIDA 8.x.

One job = one PDF = at most one language-model call. The pipeline is the
single path to a new study record, used by both the asynchronous route
(``POST /api/jobs`` + polling) and the synchronous 7.2 routes
(``POST /api/extract``, ``POST /api/extract/upload``), so credits, cost
accounting and the evidence gate behave identically whichever the client
calls.

Lifecycle::

    accept(...)   validate PDF (magic bytes, size, pages), read its text,
                  apply per-user limits, reserve 1 credit, insert `queued`
    run(job)      `running` -> extractor -> `succeeded` (study written)
                                           | `rejected` (model answered, gate refused; charge kept)
                                           | `failed`   (our side; credit refunded)

The PDF bytes never touch the database or the disk: the text is read in
``accept`` and handed to ``run`` in memory. If the process stops in between,
``recover_interrupted`` marks the orphaned jobs failed and refunds them at the
next start.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import pypdfium2 as pdfium
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import sessionmaker

from credits import CreditService, InsufficientCredits
from db import AuditLog, ExtractionJob, LLMCall, utcnow
from engines import EngineError
from extractor import EvidenceMissingError, MalformedLLMOutputError, StatisticalExtractor
from models import ExtractedEffect, StudyDatabaseEntry
from settings import Settings
from store import StudyStore

logger = logging.getLogger(__name__)

ACTIVE_STATES = ("queued", "running")


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; treat them as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass
class AcceptedJob:
    id: str
    text: str
    pages: int


@dataclass
class PdfText:
    text: str
    pages: int


def read_pdf_text(pdf_bytes: bytes, max_pages: int | None = None) -> PdfText:
    """Extract plain text with pypdfium2; raises HTTPException on bad input."""
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not pdf_bytes.lstrip()[:5].startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The file is not a PDF.")
    try:
        doc = pdfium.PdfDocument(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"PDF text extraction failed: {exc}") from exc
    try:
        pages = len(doc)
        if max_pages is not None and pages > max_pages:
            raise HTTPException(
                status_code=413,
                detail=f"PDF has {pages} pages; the limit is {max_pages}. Split the paper or upload the article only.",
            )
        parts: list[str] = []
        for page in doc:
            textpage = page.get_textpage()
            parts.append(textpage.get_text_range())
            textpage.close()
            page.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"PDF text extraction failed: {exc}") from exc
    finally:
        doc.close()
    return PdfText(text="\n".join(parts), pages=pages)


def machine_proposal_snapshot(effect: ExtractedEffect) -> dict:
    """Freeze what the model proposed before any human touches the record."""
    keep = (
        "effect_r", "effect_t", "effect_beta", "effect_df", "sample_n",
        "p_value", "ci_lower", "ci_upper", "doi_measure",
        "performance_measure", "extraction_confidence", "df_imputed",
        "beta_outside_pb_domain",
    )
    dump = effect.model_dump()
    return {k: dump.get(k) for k in keep}


class JobService:
    def __init__(
        self,
        settings: Settings,
        store_factory: Callable[[], StudyStore],
        extractor_factory: Callable[[], StatisticalExtractor],
    ) -> None:
        self.settings = settings
        # Resolved on every use so a test that swaps main._studies for a fresh
        # store (the 7.x fixture pattern) keeps jobs, ledger and studies in
        # the same database.
        self._store_factory = store_factory
        self._extractor_factory = extractor_factory
        self._slots = threading.BoundedSemaphore(max(1, settings.maida_max_running_jobs))

    @property
    def store(self) -> StudyStore:
        return self._store_factory()

    @property
    def session_factory(self) -> sessionmaker:
        return self.store.session_factory

    @property
    def credits(self) -> CreditService:
        return CreditService(self.session_factory)

    # -- queries ----------------------------------------------------------------

    def get(self, job_id: str, owner_id: str | None = None) -> ExtractionJob | None:
        with self.session_factory() as s:
            job = s.get(ExtractionJob, job_id)
        if job is None or (owner_id is not None and job.owner_id != owner_id):
            return None
        return job

    def list(self, owner_id: str, limit: int = 50) -> list[ExtractionJob]:
        stmt = (select(ExtractionJob).where(ExtractionJob.owner_id == owner_id)
                .order_by(ExtractionJob.created_at.desc(), ExtractionJob.id).limit(limit))
        with self.session_factory() as s:
            return list(s.scalars(stmt).all())

    def _count(self, owner_id: str, *, statuses: tuple[str, ...] | None = None,
               since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(ExtractionJob).where(ExtractionJob.owner_id == owner_id)
        if statuses:
            stmt = stmt.where(ExtractionJob.status.in_(statuses))
        if since is not None:
            stmt = stmt.where(ExtractionJob.created_at >= since)
        with self.session_factory() as s:
            return int(s.scalar(stmt) or 0)

    # -- accept -----------------------------------------------------------------

    def accept(self, owner_id: str, pdf_bytes: bytes, filename: str, metadata: dict[str, Any]) -> AcceptedJob:
        """Validate, apply limits, reserve the credit and queue the job."""
        s = self.settings
        # Probe the engine before charging anything: an unconfigured key is a
        # 503 with no job row, exactly as in 7.2.
        self._extractor_factory()
        limit_bytes = s.maida_max_pdf_mb * 1024 * 1024
        if len(pdf_bytes) > limit_bytes:
            raise HTTPException(status_code=413, detail=f"PDF is larger than {s.maida_max_pdf_mb} MB.")
        pdf = read_pdf_text(pdf_bytes, max_pages=s.maida_max_pages)

        if s.cloud_mode:
            # Balance first: "no credits" is the clearer answer when both apply,
            # and it costs one indexed read.
            if self.credits.balance(owner_id) < 1:
                raise HTTPException(status_code=402, detail="No credits left. Ask the operator for more credits.")
            if self._count(owner_id, statuses=ACTIVE_STATES) >= s.maida_max_running_jobs_per_user:
                raise HTTPException(status_code=429, detail="An extraction is already running for your account; wait for it to finish.")
            window = utcnow() - timedelta(hours=1)
            if self._count(owner_id, since=window) >= s.maida_jobs_per_hour:
                raise HTTPException(status_code=429, detail=f"Rate limit: at most {s.maida_jobs_per_hour} extractions per hour.")

        job_id = str(uuid.uuid4())
        with self.session_factory() as db:
            db.add(ExtractionJob(
                id=job_id, owner_id=owner_id, status="queued", filename=(filename or "")[:300],
                size_bytes=len(pdf_bytes), pages=pdf.pages, metadata_json=dict(metadata),
                credits_charged=0, created_at=utcnow(),
            ))
            db.commit()
        if s.cloud_mode:
            try:
                self.credits.charge(owner_id, job_id, 1)
            except InsufficientCredits as exc:
                self._finish(job_id, "failed", error_code="no_credits", error_message=str(exc))
                raise HTTPException(status_code=402, detail="No credits left. Ask the operator for more credits.") from exc
            with self.session_factory() as db:
                db.execute(update(ExtractionJob).where(ExtractionJob.id == job_id).values(credits_charged=1))
                db.commit()
        return AcceptedJob(id=job_id, text=pdf.text, pages=pdf.pages)

    # -- run --------------------------------------------------------------------

    def _finish(self, job_id: str, status: str, *, error_code: str | None = None,
                error_message: str | None = None, study_id: str | None = None,
                model: str | None = None) -> None:
        with self.session_factory() as db:
            job = db.get(ExtractionJob, job_id)
            if job is None:
                return
            job.status = status
            job.error_code = error_code
            job.error_message = (error_message or "")[:2000] or None
            job.study_id = study_id
            if model:
                job.model = model
            job.finished_at = utcnow()
            db.commit()

    def _record_call(self, job_id: str, owner_id: str, engine: Any, outcome: str) -> None:
        usage = getattr(engine, "last_usage", None) or {}
        inp = int(usage.get("input_tokens", 0) or 0)
        out = int(usage.get("output_tokens", 0) or 0)
        cost = (inp * self.settings.llm_price_input_per_mtok + out * self.settings.llm_price_output_per_mtok) / 1_000_000
        with self.session_factory() as db:
            db.add(LLMCall(
                job_id=job_id, owner_id=owner_id, provider=getattr(engine, "provider", ""),
                model=getattr(engine, "model", ""), input_tokens=inp, output_tokens=out,
                cost_usd=round(cost, 6), latency_ms=int(getattr(engine, "last_latency_ms", 0) or 0),
                outcome=outcome, created_at=utcnow(),
            ))
            db.commit()

    def _refund(self, job_id: str, owner_id: str, note: str) -> None:
        if not self.settings.cloud_mode:
            return
        with self.session_factory() as db:
            job = db.get(ExtractionJob, job_id)
            charged = int(job.credits_charged) if job else 0
        if charged > 0:
            self.credits.refund(owner_id, job_id, charged, note=note)
            with self.session_factory() as db:
                db.execute(update(ExtractionJob).where(ExtractionJob.id == job_id).values(credits_charged=0))
                db.commit()

    def run(self, job_id: str, owner_id: str, text: str, metadata: dict[str, Any]) -> StudyDatabaseEntry | None:
        """Execute one accepted job. Returns the study on success, else None.

        Never raises: every outcome is written to the job row so a client that
        polls sees it. The synchronous routes translate the row back into the
        7.2 HTTP status codes (see ``raise_for_job``).
        """
        with self._slots:
            with self.session_factory() as db:
                db.execute(update(ExtractionJob).where(ExtractionJob.id == job_id)
                           .values(status="running", started_at=utcnow()))
                db.commit()
            try:
                extractor = self._extractor_factory()
            except HTTPException as exc:
                self._finish(job_id, "failed", error_code="no_api_key", error_message=str(exc.detail))
                self._refund(job_id, owner_id, "extraction unavailable")
                return None
            engine = getattr(extractor, "_engine", None)
            model = getattr(engine, "model", None)
            try:
                effect = extractor.extract_from_text(text, metadata)
            except EvidenceMissingError as exc:
                self._record_call(job_id, owner_id, engine, "evidence_missing")
                self._finish(job_id, "rejected", error_code="evidence_missing", model=model, error_message=(
                    "Extraction rejected: the model proposed statistics without verbatim "
                    f"evidence from the paper ({exc}). No record was created."))
                return None
            except MalformedLLMOutputError as exc:
                self._record_call(job_id, owner_id, engine, "malformed_output")
                self._finish(job_id, "rejected", error_code="malformed_output", model=model, error_message=(
                    f"Extraction rejected: malformed model output ({exc}). No record was created."))
                return None
            except EngineError as exc:
                self._record_call(job_id, owner_id, engine, "provider_error")
                self._finish(job_id, "failed", error_code="provider_error", model=model,
                             error_message=f"Model provider error: {exc}")
                self._refund(job_id, owner_id, "provider error")
                return None
            except Exception as exc:  # noqa: BLE001 - every failure must land in the job row
                logger.exception("Extraction job %s failed", job_id)
                self._finish(job_id, "failed", error_code="internal_error", model=model, error_message=str(exc))
                self._refund(job_id, owner_id, "internal error")
                return None

            self._record_call(job_id, owner_id, engine, "ok")
            entry = StudyDatabaseEntry(**effect.model_dump())
            entry.machine_proposal = machine_proposal_snapshot(effect)
            self.store.put(entry, owner_id=owner_id)
            self._finish(job_id, "succeeded", study_id=entry.study_id, model=model)
            with self.session_factory() as db:
                db.add(AuditLog(owner_id=owner_id, action="extract", study_id=entry.study_id,
                                detail={"job_id": job_id, "model": model}, created_at=utcnow()))
                db.commit()
            return entry

    def raise_for_job(self, job: ExtractionJob) -> None:
        """Map a finished job's outcome onto the 7.2 synchronous status codes."""
        if job.status == "succeeded":
            return
        code = job.error_code or ""
        detail = job.error_message or "Extraction failed."
        if job.status == "rejected":
            raise HTTPException(status_code=422, detail=detail)
        if code == "no_api_key":
            raise HTTPException(status_code=503, detail=detail)
        if code == "provider_error":
            raise HTTPException(status_code=502, detail=detail)
        raise HTTPException(status_code=500, detail=detail)

    # -- startup ----------------------------------------------------------------

    def recover_interrupted(self) -> int:
        """Fail and refund jobs left queued/running by a previous process."""
        with self.session_factory() as db:
            rows = db.scalars(select(ExtractionJob).where(ExtractionJob.status.in_(ACTIVE_STATES))).all()
            orphans = [(j.id, j.owner_id) for j in rows]
        for job_id, owner_id in orphans:
            self._finish(job_id, "failed", error_code="interrupted",
                         error_message="The server restarted before this extraction finished.")
            self._refund(job_id, owner_id, "server restarted")
        if orphans:
            logger.warning("Recovered %d interrupted extraction job(s)", len(orphans))
        return len(orphans)

    # -- serialisation ------------------------------------------------------

    @staticmethod
    def to_dict(job: ExtractionJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "status": job.status,
            "filename": job.filename,
            "size_bytes": job.size_bytes,
            "pages": job.pages,
            "metadata": job.metadata_json or {},
            "study_id": job.study_id,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "model": job.model,
            "credits_charged": job.credits_charged,
            "created_at": _aware(job.created_at),
            "started_at": _aware(job.started_at),
            "finished_at": _aware(job.finished_at),
        }
