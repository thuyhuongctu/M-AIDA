"""Start the 8.0 backend in auth mode "mock" with a deterministic fake engine,
serving the built frontend, for the browser end-to-end run (run_e2e.py).

Never use outside tests: the fake engine answers from the PDF text itself
("r = X (n = N)"), which is exactly the invented-record behaviour the real
pipeline forbids (finding E1). It exists so the whole browser flow - sign in,
upload, poll, verify, lock, export - can be exercised without a model key.

    MAIDA_E2E_PORT=8899 python backend/tests/e2e/serve_mock.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("MAIDA_AUTH_MODE", "mock")
os.environ.setdefault("MAIDA_DB_PATH", str(Path(tempfile.mkdtemp(prefix="maida-e2e-")) / "e2e.db"))
os.environ.setdefault("MAIDA_ADMIN_EMAILS", "operator@example.org")
os.environ.setdefault("MAIDA_INVITED_EMAILS", "@example.org")
os.environ.setdefault("MAIDA_BETA_CREDITS", "3")
os.environ.setdefault("MAIDA_PAYMENTS", "mock")  # fake checkout, no money moves
os.environ.setdefault("MAIDA_FRONTEND_DIR", str(ROOT / "frontend" / "build"))
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-e2e-not-real")
os.environ.setdefault("LLM_MODEL", "fake-e2e-model")

import main  # noqa: E402
from extractor import StatisticalExtractor  # noqa: E402


class EchoEngine:
    """Returns statistics quoted from the PDF text; no evidence when absent."""

    provider = "fake"
    model = "fake-e2e-model"

    def __init__(self) -> None:
        self.last_usage = None
        self.last_latency_ms = 0

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        self.last_usage = {"input_tokens": 900, "output_tokens": 120}
        self.last_latency_ms = 5
        m = re.search(r"r = (-?[\d.]+) \(n = (\d+)\)", user)
        if not m:
            return json.dumps({"effect_r": 0.2, "sample_n": 10})  # no evidence -> rejected
        return json.dumps({
            "effect_r": float(m.group(1)),
            "sample_n": int(m.group(2)),
            "evidence_page": 1,
            "evidence_quote": m.group(0),
            "n_evidence_page": 1,
            "n_evidence_quote": f"n = {m.group(2)}",
            "doi_measure": "FSTS",
            "performance_measure": "ACC",
        })


main._get_extractor = lambda: StatisticalExtractor(engine=EchoEngine())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(main.app, host="127.0.0.1", port=int(os.environ.get("MAIDA_E2E_PORT", "8899")), log_level="warning")
