"""Shared pytest setup for backend/tests/.

Module-level code here runs before pytest imports any test_*.py file in this
directory, so MAIDA_ADMIN_KEY is set before main.py resolves it into the
admin_key_guard middleware (7.2.2). Test files send ADMIN_HEADERS on every
TestClient(...) they build.
"""

from __future__ import annotations

import os

TEST_ADMIN_KEY = "test-admin-key-do-not-use-in-prod"
os.environ.setdefault("MAIDA_ADMIN_KEY", TEST_ADMIN_KEY)

ADMIN_HEADERS = {"X-MAIDA-Admin-Key": TEST_ADMIN_KEY}
