#!/usr/bin/env python3
"""Defense demo runner: start the real M-AIDA backend pre-loaded with real data.

What this script does
---------------------
1. Imports the production FastAPI app from ``backend/main.py`` (no core code
   is modified; this is a packaging harness only).
2. Seeds the in-memory study store from a CSV exported from the dissertation's
   locked P6 analysis database:
   - by default the bundled subset ``demo/demo_seed.csv`` (18 real effect
     rows from 13 published studies);
   - or the full database when ``MAIDA_SEED_CSV`` points to a local copy of
     ``p6_study_database.csv`` (kept outside this repository until the
     dissertation is published).
3. Serves a dependency-free web UI (``demo/ui.html``) at ``/`` so the whole
   product runs with Python only; the React client in ``frontend/`` remains
   the full development UI.

Seeding rules (documented so nothing is silently invented)
----------------------------------------------------------
- Rows with ``is_estimated = 0`` carry a directly reported Pearson r; they are
  seeded with ``extraction_confidence = 1.0`` and imported as verified+locked,
  because their values come from the PI-locked dissertation database.
- Rows with ``is_estimated = 1`` carry an r obtained through a conversion or
  estimation route; they are seeded with ``extraction_confidence = 0.6`` and
  left UNLOCKED with ``requires_verification = True`` plus a frozen
  ``machine_proposal`` snapshot, so the human-verification workflow
  (review -> override -> approve -> lock -> 409 on further edits) can be
  demonstrated live on real records. Set ``MAIDA_LOCK_ALL=1`` to lock these
  too.
- The CSV's ``cdai`` column is the categorical class (L/M/H) used in the
  dissertation, not the 0-1 CDAI score, so ``cdai_score`` is left empty and
  the class is recorded in the PI notes instead.
- Paper titles are not stored in the analysis CSV; entries display
  "Author (Year)" and the full citation lives in the dissertation reference
  list.

Run from the repository root:

    pip install -r backend/requirements.txt
    python demo/run_defense.py

Then open http://localhost:8765/ in a browser. Live PDF extraction needs
LLM_API_KEY (or ANTHROPIC_API_KEY) in ``backend/.env``; without it the
extraction endpoint honestly returns 503 and every other feature still works.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
# settings.py reads .env relative to the working directory; run beside it so
# backend/.env (API key, port) is honoured no matter where the user started.
os.chdir(BACKEND)

from fastapi.responses import FileResponse  # noqa: E402

import main  # noqa: E402  (the real app: backend/main.py)
from models import StudyDatabaseEntry  # noqa: E402

SEED_CSV = Path(os.environ.get("MAIDA_SEED_CSV", ROOT / "demo" / "demo_seed.csv"))
LOCK_ALL = os.environ.get("MAIDA_LOCK_ALL", "") == "1"
UI_FILE = ROOT / "demo" / "ui.html"

PROVENANCE = (
    "Imported from the PI-locked P6 analysis database of the dissertation "
    "(Do Thuy Huong and Phan Anh Tu); value as verified by the PI."
)


def _to_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _entry_from_row(row: dict[str, str]) -> StudyDatabaseEntry:
    estimated = row["is_estimated"].strip() == "1"
    confidence = 0.6 if estimated else 1.0
    pending = estimated and not LOCK_ALL

    notes_bits = [PROVENANCE]
    if row.get("cdai", "").strip():
        notes_bits.append(f"CDAI class in source CSV: {row['cdai'].strip()}.")
    if row.get("notes", "").strip():
        notes_bits.append(f"Coder note: {row['notes'].strip()}")

    entry = StudyDatabaseEntry(
        study_id=row["effect_id"].strip(),
        paper_title=f"{row['author'].strip()} ({row['year'].strip()})",
        authors=row["author"].strip(),
        year=int(row["year"]),
        country=row["country"].strip(),
        sample_n=_to_int(row["n"]),
        sample_start=_to_int(row["sample_start"]),
        sample_end=_to_int(row["sample_end"]),
        effect_r=float(row["r"]),
        doi_measure=row["doi_type"].strip() or None,
        performance_measure=row["fp_type"].strip() or None,
        icrv_regime=row["icrv"].strip() or None,
        dpl_phase=row["dpl"].strip() or None,
        extraction_confidence=confidence,
        requires_verification=pending,
        pi_locked=not pending,
        pi_notes="" if pending else " ".join(notes_bits),
        locked_at=None if pending else datetime.utcnow(),
    )
    if pending:
        entry.machine_proposal = main._machine_proposal_snapshot(entry)
    return entry


def seed() -> tuple[int, int]:
    rows = [
        r
        for r in csv.DictReader(open(SEED_CSV, encoding="utf-8"))
        if r.get("include_flag", "1").strip() != "0"
    ]
    locked = pending = 0
    for row in rows:
        entry = _entry_from_row(row)
        main._studies[entry.study_id] = entry
        if entry.pi_locked:
            locked += 1
        else:
            pending += 1
    return locked, pending


@main.app.get("/", include_in_schema=False)
def demo_ui() -> FileResponse:
    return FileResponse(UI_FILE, media_type="text/html")


if __name__ == "__main__":
    import uvicorn

    locked, pending = seed()
    port = main.settings.maida_port
    print(f"M-AIDA defense demo: seeded {locked} locked + {pending} pending "
          f"effect records from {SEED_CSV.name}")
    print(f"Open http://localhost:{port}/  (API docs at /docs)")
    uvicorn.run(main.app, host="0.0.0.0", port=port)
