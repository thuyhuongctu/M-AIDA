import csv
import hashlib
import json
from pathlib import Path


SAMPLING = Path(__file__).parents[1] / "sampling"
MANIFEST = SAMPLING / "candidate_sample_v1.csv"
METADATA = SAMPLING / "candidate_sample_v1.metadata.json"


def test_committed_candidate_manifest_matches_metadata():
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    assert metadata["status"] == "PROVISIONAL"
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == metadata["candidate_manifest_sha256"]
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    primary = [row for row in rows if row["selection_group"] == "PRIMARY"]
    reserve = [row for row in rows if row["selection_group"] == "RESERVE"]
    assert len(primary) == metadata["primary_count"] == 40
    assert len(reserve) == metadata["reserve_count"] == 10
    assert all(row["full_text_status"] == "TO_CONFIRM" for row in primary)
    assert all(row["development_use"] == "TO_CONFIRM" for row in primary)
    payload = "\n".join(
        f"{row['selection_group']}|{row['sample_order']}|{row['study_id']}" for row in rows
    ) + "\n"
    assert hashlib.sha256(payload.encode()).hexdigest() == metadata["selection_fingerprint_sha256"]
    excluded = set(metadata["excluded_demo_study_ids"]) | set(metadata["excluded_estimated_study_ids"])
    assert not ({row["study_id"] for row in rows} & excluded)
