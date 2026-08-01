import csv
import json
from pathlib import Path

from validation.freeze_validation_sample import build_lock, inspect_manifest
from validation.select_validation_sample import (
    build_candidate,
    demo_study_ids,
    read_rows,
    selection_fingerprint,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_selection_is_deterministic_stratified_and_excludes_demo():
    source = read_rows(FIXTURES / "source_sampling.csv")
    excluded = demo_study_ids(FIXTURES / "demo_sampling.csv")
    first = build_candidate(source, excluded, 9, 1, "fixed-seed")
    second = build_candidate(source, excluded, 9, 1, "fixed-seed")
    assert first == second
    assert "A" not in {row["study_id"] for row in first}
    primary = [row for row in first if row["selection_group"] == "PRIMARY"]
    assert len(primary) == 9
    assert {f"{row['dpl']}|{row['icrv']}" for row in primary} == {
        "PRE|I", "PRE|II", "SPN|III", "SPN|MX", "SPN|FR",
        "FOL|I", "FOL|II", "FOL|III", "FOL|MX",
    }


def write_manifest(path: Path, statuses: tuple[str, str]) -> None:
    fields = ["selection_group", "study_id", "full_text_status", "development_use"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(30):
            writer.writerow({
                "selection_group": "PRIMARY",
                "study_id": f"S{index:03d}",
                "full_text_status": statuses[0],
                "development_use": statuses[1],
            })


def test_freeze_rejects_unconfirmed_gates(tmp_path):
    manifest = tmp_path / "candidate.csv"
    write_manifest(manifest, ("TO_CONFIRM", "TO_CONFIRM"))
    _, blockers = inspect_manifest(manifest)
    assert len(blockers) == 60


def test_freeze_builds_lock_after_gates_pass(tmp_path):
    manifest = tmp_path / "candidate.csv"
    write_manifest(manifest, ("AVAILABLE", "NOT_USED"))
    primary, blockers = inspect_manifest(manifest)
    assert blockers == []
    metadata = {
        "seed": "fixed",
        "source": {"git_blob_sha": "abc"},
        "scope": "global published I–P literature; Asian institutional interpretation where relevant",
        "osf": {"code": "Z37KN", "doi": "10.17605/OSF.IO/Z37KN"},
    }
    metadata["selection_fingerprint_sha256"] = selection_fingerprint([
        {"selection_group": "PRIMARY", "sample_order": "", "study_id": f"S{index:03d}"}
        for index in range(30)
    ])
    lock = build_lock(manifest, json.loads(json.dumps(metadata)), primary)
    assert lock["status"] == "LOCKED"
    assert lock["primary_count"] == 30
