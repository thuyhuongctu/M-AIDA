"""Browser end-to-end run for M-AIDA 8.0 (Playwright, Chromium).

Flow: sign in (mock) -> dashboard shows 3 credits -> upload a PDF -> job
settles -> record shown -> credits 2 -> second user cannot see it ->
verify -> lock -> CSV export -> account ledger -> sign out.

Prerequisites: `npm run build` in frontend/, `pip install playwright` in the
backend venv and a Chromium Playwright can find. Starts serve_mock.py itself.

    python backend/tests/e2e/run_e2e.py [--headed] [--shots DIR]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))  # backend/tests, for conftest

from conftest import make_minimal_pdf  # noqa: E402

PORT = int(os.environ.get("MAIDA_E2E_PORT", "8899"))
BASE = f"http://127.0.0.1:{PORT}"


def wait_for_server(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("backend did not start")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--shots", default="")
    args = ap.parse_args()
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import expect, sync_playwright

    server = subprocess.Popen([sys.executable, str(HERE / "serve_mock.py")],
                              env={**os.environ, "MAIDA_E2E_PORT": str(PORT)})
    try:
        wait_for_server()
        good_pdf = make_minimal_pdf("Internationalisation and performance. r = 0.31 (n = 240).")
        bad_pdf = make_minimal_pdf("A paper that reports nothing usable.")

        with sync_playwright() as p:
            # A Chromium outside Playwright's own cache can be pointed at with
            # MAIDA_E2E_CHROMIUM (the cloud container ships one preinstalled).
            exe = os.environ.get("MAIDA_E2E_CHROMIUM") or None
            browser = p.chromium.launch(headless=not args.headed, executable_path=exe)
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()

            def shot(name: str) -> None:
                if shots:
                    page.screenshot(path=str(shots / f"{name}.png"), full_page=True)

            # 1. Sign in
            page.goto(BASE)
            expect(page.get_by_test_id("login-card")).to_be_visible()
            # 3D logo: WebGL scene when the browser has WebGL, flat wordmark otherwise
            expect(page.get_by_test_id("logo3d")).to_have_attribute("data-state", re.compile("ready|fallback"), timeout=20000)
            print("[e2e] login 3D logo:", page.get_by_test_id("logo3d").get_attribute("data-state"))
            page.wait_for_timeout(800)
            shot("01-login")
            # Contact: both authors, presented as a research project, no institutional address
            page.get_by_test_id("contact-open").click()
            contact = page.get_by_test_id("contact-dialog")
            expect(contact).to_be_visible()
            expect(contact).to_contain_text("Assoc. Prof. Phan Anh Tu")
            expect(contact).to_contain_text("patu@ctu.edu.vn")
            expect(contact).to_contain_text("research project")
            expect(contact).not_to_contain_text("3/2 Street")
            expect(contact).not_to_contain_text("Vice Rector")
            shot("01b-contact")
            page.keyboard.press("Escape")
            expect(contact).to_be_hidden()
            page.fill("#login-email", "alice@example.org")
            page.click("text=Sign in (test mode)")
            expect(page.get_by_test_id("dashboard")).to_be_visible()
            expect(page.get_by_test_id("credits-balance")).to_have_text("3")
            expect(page.get_by_test_id("header-user")).to_contain_text("alice@example.org")
            # First sign-in: the guided tour opens; two steps switch tabs, then skip.
            expect(page.get_by_test_id("tour")).to_be_visible()
            shot("02a-tour")
            page.get_by_test_id("tour-next").click()
            expect(page.get_by_test_id("tour")).to_contain_text("credits")
            page.get_by_test_id("tour-next").click()
            expect(page.get_by_test_id("tab-extract")).to_have_attribute("aria-selected", "true")
            page.get_by_test_id("tour-skip").click()
            expect(page.get_by_test_id("tour")).to_have_count(0)
            page.get_by_test_id("tab-dashboard").click()
            shot("02-dashboard-empty")
            # header logo opens the 3D dialog; three.js is loaded only now
            page.get_by_test_id("logo-3d-open").click()
            dlg = page.get_by_test_id("logo3d-dialog")
            expect(dlg).to_be_visible()
            expect(dlg.get_by_test_id("logo3d")).to_have_attribute("data-state", re.compile("ready|fallback"), timeout=20000)
            page.wait_for_timeout(800)
            shot("02b-logo3d-dialog")
            page.keyboard.press("Escape")
            expect(dlg).to_be_hidden()

            # 2. Upload and extract
            page.get_by_test_id("tab-extract").click()
            page.set_input_files("input[type=file]", {"name": "paper-240.pdf", "mimeType": "application/pdf", "buffer": good_pdf})
            page.fill("#ex-authors", "Doe, J.")
            page.fill("#ex-country", "Vietnam")
            page.get_by_test_id("extract-submit").click()
            expect(page.get_by_test_id("result-card")).to_be_visible(timeout=20_000)
            expect(page.get_by_test_id("result-card")).to_contain_text("0.3100")
            shot("03-extracted")

            # 3. A rejected upload keeps the charge and says so
            page.set_input_files("input[type=file]", {"name": "no-evidence.pdf", "mimeType": "application/pdf", "buffer": bad_pdf})
            page.get_by_test_id("extract-submit").click()
            expect(page.get_by_test_id("extract-error")).to_contain_text("Rejected", timeout=20_000)
            shot("04-rejected")

            # 4. Dashboard: 1 credit left, two jobs, one record waiting for review
            page.get_by_test_id("tab-dashboard").click()
            expect(page.get_by_test_id("credits-balance")).to_have_text("1")
            rows = page.get_by_test_id("job-row")
            expect(rows).to_have_count(2)
            expect(rows.first).to_have_attribute("data-status", "rejected")
            expect(rows.nth(1)).to_have_attribute("data-status", "succeeded")
            expect(page.get_by_test_id("next-up")).to_contain_text("1 record waiting")
            shot("05-dashboard-jobs")

            # 5. "Continue reviewing" opens the record in the three-pane review screen
            page.get_by_test_id("continue-review").click()
            expect(page.get_by_test_id("review-screen")).to_be_visible()
            expect(page.get_by_test_id("verification-panel")).to_be_visible()
            expect(page.get_by_test_id("evidence-card")).to_contain_text("r = 0.31")
            # approval needs a note
            page.get_by_test_id("vp-approve").click()
            expect(page.get_by_test_id("vp-error")).to_contain_text("Required")
            page.get_by_test_id("vp-notes").fill("Checked r and n against table 3 of the paper.")
            page.get_by_test_id("vp-approve").click()
            expect(page.get_by_test_id("vp-approve")).to_contain_text("Approved", timeout=10_000)
            expect(page.get_by_test_id("rv-item").first).to_have_attribute("data-state", "approved")
            shot("06-approved")
            # lock: the dialog demands the study id
            page.get_by_test_id("vp-lock").click()
            dialog = page.get_by_test_id("lock-dialog")
            expect(dialog).to_be_visible()
            study_id = dialog.locator("code").inner_text().strip()
            expect(page.get_by_test_id("lock-confirm")).to_be_disabled()
            page.get_by_test_id("lock-id-input").fill(study_id)
            page.get_by_test_id("lock-confirm").click()
            expect(page.get_by_test_id("locked-banner")).to_be_visible(timeout=10_000)
            expect(page.get_by_test_id("rv-item").first).to_have_attribute("data-state", "locked")
            shot("06-locked")
            # keyboard navigation does not crash with a single record
            page.keyboard.press("j")
            page.keyboard.press("k")

            # CSV export from the Dataset tab: intercept the download
            page.get_by_test_id("tab-dataset").click()
            expect(page.get_by_test_id("dataset-panel")).to_contain_text("1")
            # forest plot: one locked row (r = 0.31, n = 240 -> Fisher-z CI) and the pooled preview
            forest = page.get_by_test_id("forest-plot")
            expect(forest).to_contain_text("0.310 [0.191, 0.420]")
            expect(forest).to_contain_text("Pooled (preview)")
            with page.expect_download(timeout=10_000) as dl:
                page.get_by_test_id("export-csv").click()
            csv_path = dl.value.path()
            text = Path(csv_path).read_text(encoding="utf-8")
            assert "paper-240" in text or "0.31" in text, text[:200]
            shot("06b-dataset")

            # 6. Account tab: ledger shows grant / extraction x2
            page.get_by_test_id("tab-account").click()
            expect(page.get_by_test_id("account-credits")).to_have_text("1")
            expect(page.locator(".ledger-table tbody tr")).to_have_count(3)
            shot("07-account")

            # 7. Isolation: a second user sees nothing of Alice's
            page.get_by_test_id("sign-out").click()
            expect(page.get_by_test_id("login-card")).to_be_visible()
            page.fill("#login-email", "bob@example.org")
            page.click("text=Sign in (test mode)")
            expect(page.get_by_test_id("credits-balance")).to_have_text("3")
            expect(page.get_by_test_id("job-row")).to_have_count(0)
            page.get_by_test_id("tab-verify").click()
            expect(page.get_by_test_id("rv-item")).to_have_count(0)
            shot("08-bob-empty")

            # 8. Operator: grant credits, see usage
            page.get_by_test_id("tab-account").click()
            page.get_by_test_id("sign-out").click()
            page.fill("#login-email", "operator@example.org")
            page.click("text=Sign in (test mode)")
            page.get_by_test_id("tab-account").click()
            expect(page.get_by_test_id("admin-tools")).to_be_visible()
            page.fill("#grant-email", "alice@example.org")
            page.fill("#grant-amount", "5")
            page.get_by_role("button", name="Grant").click()
            expect(page.locator(".grant-form .hint-text")).to_contain_text("6 credits", timeout=10_000)
            expect(page.locator(".usage-line")).to_contain_text("2 calls")
            shot("09-operator")

            # 9. Vietnamese toggle renders
            page.click(".lang-toggle")
            expect(page.get_by_test_id("tab-dashboard")).to_have_text("Bảng điều khiển")
            shot("10-vietnamese")

            # 10. Legal pages are served next to the app (static, bilingual)
            page.goto(f"{BASE}/legal/terms.html")
            expect(page.locator("h1#en")).to_contain_text("Terms of Service")
            expect(page.locator("h1#vi")).to_contain_text("Điều khoản dịch vụ")
            shot("11-terms")
            page.goto(f"{BASE}/legal/privacy.html")
            expect(page.locator("h1#en")).to_contain_text("Privacy Policy")
            shot("12-privacy")

            browser.close()
        print("E2E passed.")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
