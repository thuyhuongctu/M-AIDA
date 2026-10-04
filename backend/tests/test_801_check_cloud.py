"""8.0: the cloud preflight (backend/check_cloud.py) reads a .env file, judges each
item and exits non-zero on anything that must not go live."""

from __future__ import annotations

import io
import json

import check_cloud


def _run(tmp_path, monkeypatch, env_text: str, *extra: str) -> tuple[int, str]:
    env = tmp_path / "x.env"
    env.write_text(env_text, encoding="utf-8")
    for key in ("MAIDA_AUTH_MODE", "MAIDA_DB_PATH", "DATABASE_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY",
                "SUPABASE_JWT_SECRET", "MAIDA_ADMIN_EMAILS", "MAIDA_DEMO_MODE", "ANTHROPIC_API_KEY", "LLM_API_KEY",
                "MAIDA_PAYMENTS", "PAYOS_CLIENT_ID", "PAYOS_API_KEY", "PAYOS_CHECKSUM_KEY", "MAIDA_PUBLIC_URL",
                "MAIDA_CREDIT_PACKS"):
        monkeypatch.delenv(key, raising=False)
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    code = check_cloud.main(["--env", str(env), "--no-llm", *extra])
    return code, out.getvalue()


def test_env_loader_handles_quotes_and_comments(tmp_path, monkeypatch):
    env = tmp_path / "a.env"
    env.write_text('# c\nA=1\nB="two words" # trailing\nC=\'x\'\n\nD=a=b\n', encoding="utf-8")
    for k in "ABCD":
        monkeypatch.delenv(k, raising=False)
    check_cloud.load_env_file(str(env))
    import os

    assert os.environ["A"] == "1" and os.environ["B"] == "two words"
    assert os.environ["C"] == "x" and os.environ["D"] == "a=b"


def test_single_operator_sqlite_passes_with_warnings(tmp_path, monkeypatch):
    code, out = _run(tmp_path, monkeypatch, f"MAIDA_AUTH_MODE=admin_key\nMAIDA_DB_PATH={tmp_path / 'c.db'}\n")
    assert code == 0 and "LƯU Ý" in out and "Mọi mục bắt buộc đạt" in out


def test_mock_mode_and_demo_mode_are_refused(tmp_path, monkeypatch):
    code, out = _run(tmp_path, monkeypatch, f"MAIDA_AUTH_MODE=mock\nMAIDA_DB_PATH={tmp_path / 'c.db'}\nMAIDA_DEMO_MODE=true\n")
    assert code == 1 and "mock" in out and "MAIDA_DEMO_MODE=true" in out


def test_supabase_mode_checks_jwks_and_anon_key(tmp_path, monkeypatch):
    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    jwks = json.dumps({"keys": [{"kid": "k", "alg": "ES256", "kty": "EC"}]}).encode()
    monkeypatch.setattr(check_cloud.urllib.request, "urlopen", lambda url, timeout=10: FakeResp(jwks))
    code, out = _run(tmp_path, monkeypatch,
                     f"MAIDA_AUTH_MODE=supabase\nSUPABASE_URL=https://abc.supabase.co\nSUPABASE_ANON_KEY=sb_pub\n"
                     f"MAIDA_ADMIN_EMAILS=a@b.c\nMAIDA_DB_PATH={tmp_path / 'c.db'}\n")
    assert code == 0 and "JWKS: 1 khóa (ES256)" in out

    empty = json.dumps({"keys": []}).encode()
    monkeypatch.setattr(check_cloud.urllib.request, "urlopen", lambda url, timeout=10: FakeResp(empty))
    code, out = _run(tmp_path, monkeypatch,
                     f"MAIDA_AUTH_MODE=supabase\nSUPABASE_URL=https://abc.supabase.co\nMAIDA_DB_PATH={tmp_path / 'c.db'}\n")
    assert code == 1 and "SUPABASE_ANON_KEY trống" in out and "SUPABASE_JWT_SECRET trống" in out


def test_payments_need_complete_payos_settings(tmp_path, monkeypatch):
    base = f"MAIDA_AUTH_MODE=mock\nMAIDA_DB_PATH={tmp_path / 'c.db'}\nMAIDA_PAYMENTS=payos\n"
    code, out = _run(tmp_path, monkeypatch, base + "PAYOS_CLIENT_ID=cid1234\nPAYOS_API_KEY=k\n")
    assert code == 1 and "PAYOS_CHECKSUM_KEY" in out and "MAIDA_PUBLIC_URL" in out

    code, out = _run(tmp_path, monkeypatch, base + "PAYOS_CLIENT_ID=cid1234\nPAYOS_API_KEY=k\n"
                     "PAYOS_CHECKSUM_KEY=c\nMAIDA_PUBLIC_URL=https://maida.example.org\n")
    assert "https://maida.example.org/api/payments/payos/webhook" in out
    assert "giá NHÁP" in out and "...1234" in out and "149.000 đ" in out
    assert "PAYOS_CHECKSUM_KEY=c" not in out  # secrets are never printed


def test_payments_off_is_reported_but_not_a_failure(tmp_path, monkeypatch):
    code, out = _run(tmp_path, monkeypatch, f"MAIDA_AUTH_MODE=admin_key\nMAIDA_DB_PATH={tmp_path / 'c.db'}\n")
    assert code == 0 and "MAIDA_PAYMENTS trống" in out
