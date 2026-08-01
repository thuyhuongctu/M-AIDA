#!/usr/bin/env python3
"""Run the real M-AIDA API as a resilient, presenter-controlled defense demo."""

from __future__ import annotations

import csv
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from fastapi import Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402

import main  # noqa: E402
from models import StudyDatabaseEntry  # noqa: E402

SEED_CSV = Path(os.environ.get("MAIDA_SEED_CSV", ROOT / "demo" / "demo_seed.csv"))
STATE_FILE = Path(os.environ.get("MAIDA_DEMO_STATE", ROOT / "demo" / ".defense-state.json"))
LOCK_ALL = os.environ.get("MAIDA_LOCK_ALL", "") == "1"
PERSIST = os.environ.get("MAIDA_DEMO_PERSIST", "1") != "0"
PRESENTER_PIN = os.environ.get("MAIDA_DEMO_PIN") or secrets.token_urlsafe(4)
UI_FILE = ROOT / "demo" / "ui.html"
MANIFEST_FILE = ROOT / "demo" / "manifest.webmanifest"
SW_FILE = ROOT / "demo" / "sw.js"
ICON_FILE = ROOT / "demo" / "icon.svg"

PROVENANCE = (
    "Imported from the PI-locked P6 analysis database of the dissertation "
    "(Do Thuy Huong and Phan Anh Tu); value as verified by the PI."
)


def _to_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _entry_from_row(row: dict[str, str]) -> StudyDatabaseEntry:
    estimated = row["is_estimated"].strip() == "1"
    pending = estimated and not LOCK_ALL
    notes = [PROVENANCE]
    if row.get("cdai", "").strip():
        notes.append(f"CDAI class in source CSV: {row['cdai'].strip()}.")
    if row.get("notes", "").strip():
        notes.append(f"Coder note: {row['notes'].strip()}")
    entry = StudyDatabaseEntry(
        study_id=row["effect_id"].strip(),
        paper_title=f"{row['author'].strip()} ({row['year'].strip()})",
        authors=row["author"].strip(),
        year=int(row["year"]), country=row["country"].strip(),
        sample_n=_to_int(row["n"]), sample_start=_to_int(row["sample_start"]),
        sample_end=_to_int(row["sample_end"]), effect_r=float(row["r"]),
        doi_measure=row["doi_type"].strip() or None,
        performance_measure=row["fp_type"].strip() or None,
        icrv_regime=row["icrv"].strip() or None,
        dpl_phase=row["dpl"].strip() or None,
        extraction_confidence=0.6 if estimated else 1.0,
        requires_verification=pending, pi_locked=not pending,
        pi_notes="" if pending else " ".join(notes),
        locked_at=None if pending else datetime.utcnow(),
    )
    if pending:
        entry.machine_proposal = main._machine_proposal_snapshot(entry)
    return entry


def seed(*, reset: bool = False) -> tuple[int, int]:
    if reset:
        main._studies.clear()
    rows = [r for r in csv.DictReader(SEED_CSV.open(encoding="utf-8"))
            if r.get("include_flag", "1").strip() != "0"]
    for row in rows:
        entry = _entry_from_row(row)
        main._studies.put(entry)
    return counts()


def counts() -> tuple[int, int]:
    locked = sum(s.pi_locked for s in main._studies.values())
    return locked, len(main._studies) - locked


def save_state() -> None:
    if not PERSIST:
        return
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = [s.model_dump(mode="json") for s in main._studies.values()]
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def restore_or_seed() -> tuple[int, int]:
    if PERSIST and STATE_FILE.exists():
        try:
            payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            main._studies.clear()
            for item in payload:
                entry = StudyDatabaseEntry(**item)
                main._studies.put(entry)
            return counts()
        except (OSError, ValueError, TypeError):
            print("Warning: saved demo state was invalid; restoring the verified seed.")
    result = seed(reset=True)
    save_state()
    return result


@main.app.middleware("http")
async def presenter_guard(request: Request, call_next):
    mutating = request.method in {"POST", "PATCH", "PUT", "DELETE"}
    if mutating and request.headers.get("X-MAIDA-Demo-PIN") != PRESENTER_PIN:
        return JSONResponse({"detail": "Presenter PIN required."}, status_code=401)
    response = await call_next(request)
    if mutating and response.status_code < 400:
        save_state()
    return response


@main.app.get("/", include_in_schema=False)
def demo_ui() -> FileResponse:
    return FileResponse(UI_FILE, media_type="text/html")


@main.app.get("/manifest.webmanifest", include_in_schema=False)
def demo_manifest() -> FileResponse:
    return FileResponse(MANIFEST_FILE, media_type="application/manifest+json")


@main.app.get("/sw.js", include_in_schema=False)
def demo_service_worker() -> FileResponse:
    return FileResponse(SW_FILE, media_type="application/javascript")


@main.app.get("/demo-icon.svg", include_in_schema=False)
def demo_icon() -> FileResponse:
    return FileResponse(ICON_FILE, media_type="image/svg+xml")


@main.app.post("/api/demo/reset", tags=["demo"])
def reset_demo() -> dict[str, int | str]:
    locked, pending = seed(reset=True)
    save_state()
    return {"status": "reset", "locked": locked, "pending": pending}


if __name__ == "__main__":
    import uvicorn

    locked, pending = restore_or_seed()
    port = main.settings.maida_port
    print(f"M-AIDA Defense App: {locked} locked + {pending} pending records")
    print(f"Presenter PIN: {PRESENTER_PIN}")
    print(f"Open http://localhost:{port}/  (API docs: /docs)")
    uvicorn.run(main.app, host="0.0.0.0", port=port)
