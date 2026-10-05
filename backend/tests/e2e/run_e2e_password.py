"""Browser end-to-end run for the internal-trial sign-in (MAIDA_LOGIN_METHOD=password).

A stand-in for Supabase Auth (fake_supabase_auth below) answers the two calls
supabase-js makes for e-mail + password sign-in and sign-out, and signs the
session with the legacy HS256 secret the backend is also given. Everything
else is the real app: auth mode "supabase", the invitation list, the built
frontend served by the backend.

Flow: the sign-in page asks for a password and offers no magic link or Google
-> a wrong password is refused with a plain message -> an account that exists
but is not invited is refused by the backend -> the invited account signs in
and sees its 10 beta credits -> sign out returns to the sign-in page.

    python backend/tests/e2e/run_e2e_password.py [--headed] [--shots DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jwt

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
ROOT = BACKEND.parent

APP_PORT = int(os.environ.get("MAIDA_E2E_PORT", "8897"))
AUTH_PORT = APP_PORT + 1
BASE = f"http://127.0.0.1:{APP_PORT}"
SECRET = "e2e-hs256-secret-" + "x" * 32
ACCOUNTS = {"alice@example.org": "alice-pass-1", "bob@example.org": "bob-pass-1"}  # bob is not invited


def _session(email: str) -> dict:
    now = int(time.time())
    sub = "00000000-0000-4000-8000-" + format(abs(hash(email)) % 10**12, "012d")
    claims = {"sub": sub, "email": email, "aud": "authenticated", "role": "authenticated",
              "iat": now, "exp": now + 3600, "user_metadata": {"full_name": email.split("@")[0].title()}}
    user = {"id": sub, "aud": "authenticated", "role": "authenticated", "email": email,
            "app_metadata": {"provider": "email"}, "user_metadata": claims["user_metadata"],
            "created_at": "2026-10-05T00:00:00Z"}
    return {"access_token": jwt.encode(claims, SECRET, algorithm="HS256"), "token_type": "bearer",
            "expires_in": 3600, "expires_at": now + 3600, "refresh_token": "r-" + sub, "user": user}


class FakeAuth(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, code: int, body: dict | None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self._cors()
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._json(204, None)

    def do_POST(self):
        u = urlparse(self.path)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if u.path == "/auth/v1/token" and parse_qs(u.query).get("grant_type") == ["password"]:
            if ACCOUNTS.get(body.get("email", "").lower()) == body.get("password"):
                return self._json(200, _session(body["email"].lower()))
            return self._json(400, {"code": 400, "error_code": "invalid_credentials", "msg": "Invalid login credentials"})
        if u.path == "/auth/v1/logout":
            return self._json(204, None)
        return self._json(404, {"msg": "not found"})

    def do_GET(self):
        return self._json(404, {"msg": "not found"})


def wait_for(url: str, timeout: float = 40.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError(f"{url} did not answer")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--shots", default="")
    args = ap.parse_args()
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    auth = ThreadingHTTPServer(("127.0.0.1", AUTH_PORT), FakeAuth)
    threading.Thread(target=auth.serve_forever, daemon=True).start()

    env = dict(os.environ,
               MAIDA_AUTH_MODE="supabase", MAIDA_LOGIN_METHOD="password",
               SUPABASE_URL=f"http://127.0.0.1:{AUTH_PORT}", SUPABASE_ANON_KEY="sb_publishable_e2e",
               SUPABASE_JWT_SECRET=SECRET, MAIDA_INVITED_EMAILS="alice@example.org",
               MAIDA_ADMIN_EMAILS="operator@example.org", MAIDA_BETA_CREDITS="10",
               MAIDA_DB_PATH=str(Path(tempfile.mkdtemp(prefix="maida-e2e-pw-")) / "pw.db"),
               MAIDA_FRONTEND_DIR=str(ROOT / "frontend" / "build"),
               ANTHROPIC_API_KEY="sk-e2e-not-real", LLM_MODEL="fake-e2e-model", PYTHONPATH=str(BACKEND))
    env.pop("DATABASE_URL", None)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
                               "--port", str(APP_PORT), "--log-level", "warning"], cwd=str(BACKEND), env=env)
    try:
        wait_for(f"{BASE}/api/health")
        cfg = json.loads(urllib.request.urlopen(f"{BASE}/api/config").read())
        assert cfg["auth_mode"] == "supabase" and cfg["login_method"] == "password", cfg

        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as p:
            # Same convention as run_e2e.py: MAIDA_E2E_CHROMIUM points at a Chromium outside Playwright's cache.
            exe = os.environ.get("MAIDA_E2E_CHROMIUM") or None
            browser = p.chromium.launch(headless=not args.headed, executable_path=exe)
            page = browser.new_page(viewport={"width": 1280, "height": 860}, locale="en-US")
            page.goto(BASE)
            card = page.get_by_test_id("login-card")
            expect(card).to_be_visible(timeout=20000)
            pw = page.get_by_test_id("login-password")
            expect(pw).to_be_visible()
            assert page.get_by_text("Continue with Google").count() == 0, "Google sign-in must be hidden"
            assert page.get_by_text("Gửi liên kết đăng nhập").count() == 0 and page.get_by_text("Send me a sign-in link").count() == 0
            if shots:
                page.screenshot(path=str(shots / "01_login_password.png"))

            page.fill("#login-email", "alice@example.org")
            pw.fill("wrong-password")
            card.locator("button[type=submit]").click()
            expect(page.get_by_text("The e-mail or password is not correct.").or_(page.get_by_text("E-mail hoặc mật khẩu không đúng."))).to_be_visible(timeout=10000)

            page.fill("#login-email", "bob@example.org")
            pw.fill("bob-pass-1")
            card.locator("button[type=submit]").click()
            # The session is valid but the backend refuses an address that is not invited:
            # the app shows its single "not on the list" screen, never the dashboard.
            expect(page.get_by_test_id("not-invited")).to_be_visible(timeout=15000)
            if shots:
                page.screenshot(path=str(shots / "02_not_invited.png"))

            # Back to a clean sign-in page, then the invited account.
            page.context.clear_cookies()
            page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }")
            page.goto(BASE)
            expect(page.get_by_test_id("login-password")).to_be_visible(timeout=20000)
            page.fill("#login-email", "alice@example.org")
            page.get_by_test_id("login-password").fill("alice-pass-1")
            page.get_by_test_id("login-card").locator("button[type=submit]").click()
            expect(page.get_by_test_id("login-card")).to_have_count(0, timeout=20000)
            token = page.evaluate("""() => { for (const k of Object.keys(localStorage)) { if (k.startsWith('sb-')) { try { return JSON.parse(localStorage.getItem(k)).access_token } catch (e) {} } } return null }""")
            assert token, "no Supabase session stored"
            req = urllib.request.Request(f"{BASE}/api/me", headers={"Authorization": f"Bearer {token}"})
            me = json.loads(urllib.request.urlopen(req).read())
            assert me["email"] == "alice@example.org" and me["credits"] == 10 and me["role"] == "user", me
            if shots:
                page.screenshot(path=str(shots / "03_signed_in.png"))
            browser.close()
        print("E2E password sign-in: OK (password form, wrong password refused, not-invited refused, invited signed in with 10 credits)")
        return 0
    finally:
        server.terminate()
        auth.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
