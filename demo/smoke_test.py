#!/usr/bin/env python3
"""Fast smoke test for the offline M-AIDA Defense App."""

from __future__ import annotations

import os
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["MAIDA_DEMO_PIN"] = "ci-presenter-pin"
os.environ["MAIDA_DEMO_STATE"] = str(Path(tempfile.gettempdir()) / "maida-defense-ci.json")
os.environ["MAIDA_DEMO_PERSIST"] = "0"

from fastapi.testclient import TestClient  # noqa: E402
from demo import run_defense  # noqa: E402

run_defense.restore_or_seed()
client = TestClient(run_defense.main.app)

assert client.get("/").status_code == 200
assert client.get("/manifest.webmanifest").status_code == 200
assert client.get("/sw.js").status_code == 200
health = client.get("/api/health")
assert health.status_code == 200
assert health.json()["study_count"] > 0

assert client.post("/api/demo/reset").status_code == 401
reset = client.post(
    "/api/demo/reset", headers={"X-MAIDA-Demo-PIN": "ci-presenter-pin"}
)
assert reset.status_code == 200
assert reset.json()["locked"] + reset.json()["pending"] > 0

studies = client.get("/api/studies")
assert studies.status_code == 200
assert any(item["pi_locked"] for item in studies.json())

# 7.2.1: every seeded record carries a variance (7.2.0 lock gate), and the
# presenter can verify and lock a pending record during the demo.
assert all(item["variance_r"] is not None for item in studies.json() if item["effect_r"] is not None)
pending = [item for item in studies.json() if not item["pi_locked"]]
assert pending, "the seed must leave at least one pending record for the demo"
sid = pending[0]["study_id"]
pin = {"X-MAIDA-Demo-PIN": "ci-presenter-pin"}
verified = client.patch(f"/api/studies/{sid}/verify", headers=pin,
                        json={"study_id": sid, "pi_approved": True, "pi_notes": "smoke",
                              "field_overrides": {}})
assert verified.status_code == 200, verified.text
assert client.post(f"/api/studies/{sid}/lock", headers=pin).status_code == 200
header = client.get("/api/studies/export/csv").text.splitlines()[0].split(",")
assert "variance_r" in header and "metric_type" in header

print("Defense App smoke test passed.")
