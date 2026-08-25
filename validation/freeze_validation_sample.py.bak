#!/usr/bin/env python3
"""Lock a validation sampling frame only after its anti-circularity gates pass."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selection_fingerprint(path: Path) -> str:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    payload = "\n".join(
        f"{row.get('selection_group', '')}|{row.get('sample_order', '')}|{row.get('study_id', '')}"
        for row in rows
    ) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def inspect_manifest(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    primary = [row for row in rows if row.get("selection_group") == "PRIMARY"]
    blockers = []
    if not 30 <= len(primary) <= 50:
        blockers.append(f"PRIMARY sample must contain 30–50 studies; found {len(primary)}")
    ids = [row.get("study_id", "").strip() for row in primary]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        blockers.append("PRIMARY study_id values must be unique and non-blank")
    for row in primary:
        study_id = row.get("study_id", "<blank>")
        if row.get("full_text_status") != "AVAILABLE":
            blockers.append(f"{study_id}: full_text_status must be AVAILABLE")
        if row.get("development_use") != "NOT_USED":
            blockers.append(f"{study_id}: development_use must be NOT_USED")
    return primary, blockers


def build_lock(manifest: Path, metadata: dict[str, Any], primary: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "status": "LOCKED",
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_manifest_sha256": sha256_file(manifest),
        "selection_fingerprint_sha256": selection_fingerprint(manifest),
        "sampling_seed": metadata["seed"],
        "primary_count": len(primary),
        "primary_study_ids": [row["study_id"] for row in primary],
        "source": metadata["source"],
        "scope": metadata["scope"],
        "osf": metadata["osf"],
        "gate_attestations": {
            "all_primary_full_texts_available": True,
            "all_primary_studies_unused_for_development_or_prompt_tuning": True,
            "sample_locked_before_machine_predictions_are_inspected": True,
        },
        "osf_history_note": "Preserve OSF Z37KN; document this benchmark as an addendum/deviation log, not as an a-priori preregistration.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    primary, blockers = inspect_manifest(args.manifest)
    if selection_fingerprint(args.manifest) != metadata.get("selection_fingerprint_sha256"):
        blockers.append("selection identifiers/order differ from the provisional sampling frame")
    if blockers:
        print("Sampling frame NOT LOCKED:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    if not args.output:
        parser.error("--output is required after all lock gates pass")
    lock = build_lock(args.manifest, metadata, primary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Locked {len(primary)} PRIMARY studies: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
