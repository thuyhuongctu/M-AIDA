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

#: Set MAIDA_TEST_PG_URL (a maintenance URL such as
#: postgresql+psycopg://postgres@/postgres?host=/tmp/pgtest&port=55432) to run
#: the multi-user suite against a real Postgres: every test then gets a fresh
#: database cloned from MAIDA_TEST_PG_TEMPLATE (default template_supabase, a
#: database carrying the Supabase roles and default privileges).
PG_URL = os.environ.get("MAIDA_TEST_PG_URL", "")
PG_TEMPLATE = os.environ.get("MAIDA_TEST_PG_TEMPLATE", "template_supabase")


def fresh_database_url(tmp_path, name: str) -> str:
    """SQLite file under tmp_path, or a brand-new Postgres database."""
    if not PG_URL:
        return f"sqlite:///{tmp_path / (name + '.db')}"
    import uuid

    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    db = f"maida_test_{name}_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db}" TEMPLATE "{PG_TEMPLATE}"'))
    admin.dispose()
    return make_url(PG_URL).set(database=db).render_as_string(hide_password=False)


def make_minimal_pdf(text: str) -> bytes:
    """Build a minimal single-page PDF containing ``text``, with no third-party
    PDF library dependency (main.py reads PDFs with pypdfium2, which has no
    write/generation API; hand-writing the PDF avoids pulling in a separate
    generator just for test fixtures)."""
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(out)
    n = len(objects) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(out)
