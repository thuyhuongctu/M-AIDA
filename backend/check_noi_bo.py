"""Kiểm tra trước khi mở M-AIDA chạy thử nội bộ (CHAY_MAIDA_NOI_BO.bat).

Chạy thử nội bộ = máy chủ trên laptop người vận hành, mở ra Internet bằng đường
hầm Cloudflare, đăng nhập bằng e-mail + mật khẩu của tài khoản do người vận hành
tạo tay trong Supabase. Vì đường link ai có cũng mở được, script này từ chối chạy
khi cấu hình có thể để lộ khóa hoặc cho người lạ vào:

  1. MAIDA_AUTH_MODE phải là "supabase" và MAIDA_LOGIN_METHOD là "password".
  2. SUPABASE_URL có dạng https://<ref>.supabase.co.
  3. SUPABASE_ANON_KEY là khóa công khai (publishable / anon). Khóa bí mật
     (sb_secret_... hoặc JWT có role service_role) bị từ chối: /api/config gửi
     khóa này cho mọi trình duyệt.
  4. Danh sách mời không được là "*", và phải chứa e-mail quản trị.
  5. Thanh toán tắt.
  6. (Cảnh báo, không chặn) đọc được JWKS của dự án Supabase.

    python backend/check_noi_bo.py        (mã thoát 0 = được chạy)
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.request

OK, WARN, BAD = "OK  ", "CHU Y", "LOI "


def _jwt_role(token: str) -> str:
    """Role claim of an unverified JWT ("" when the string is not a JWT)."""
    parts = token.split(".")
    if len(parts) != 3:
        return ""
    try:
        pad = "=" * (-len(parts[1]) % 4)
        return str(json.loads(base64.urlsafe_b64decode(parts[1] + pad)).get("role", ""))
    except Exception:
        return ""


def key_problem(key: str) -> str:
    """Why this key must not be sent to browsers ("" when it is a public key)."""
    key = (key or "").strip()
    if not key:
        return "SUPABASE_ANON_KEY dang trong."
    if key.startswith("sb_secret_"):
        return "Day la khoa BI MAT (sb_secret_...). Dung khoa Publishable (sb_publishable_...)."
    if _jwt_role(key) == "service_role":
        return "Day la khoa service_role (bi mat). Dung khoa anon hoac Publishable."
    if not (key.startswith("sb_publishable_") or _jwt_role(key) == "anon"):
        return "Khong nhan ra khoa. Dan khoa Publishable (sb_publishable_...) o Project Settings -> API Keys."
    return ""


def invite_problem(invited: str, admins: str) -> str:
    items = [i.strip().lower() for i in invited.split(",") if i.strip()]
    if "*" in items:
        return 'MAIDA_INVITED_EMAILS khong duoc la "*" khi mo duong link ra Internet.'
    admin = [a.strip().lower() for a in admins.split(",") if a.strip()]
    if not admin:
        return "MAIDA_ADMIN_EMAILS dang trong: can it nhat mot e-mail quan tri."
    return ""


def run(env: dict[str, str], fetch_jwks: bool = True) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    say = lambda level, msg: out.append((level, msg))  # noqa: E731

    mode = env.get("MAIDA_AUTH_MODE", "")
    method = env.get("MAIDA_LOGIN_METHOD", "")
    if mode == "supabase" and method == "password":
        say(OK, "Dang nhap: Supabase, e-mail + mat khau (tai khoan tao tay).")
    else:
        say(BAD, f"MAIDA_AUTH_MODE={mode!r}, MAIDA_LOGIN_METHOD={method!r}: chay thu noi bo can supabase + password.")

    url = env.get("SUPABASE_URL", "").strip().rstrip("/")
    if re.fullmatch(r"https://[a-z0-9]{20}\.supabase\.co", url):
        say(OK, f"SUPABASE_URL = {url}")
    else:
        say(BAD, f"SUPABASE_URL khong dung dang https://<ma du an>.supabase.co: {url!r}")

    problem = key_problem(env.get("SUPABASE_ANON_KEY", ""))
    say(BAD if problem else OK, problem or "SUPABASE_ANON_KEY la khoa cong khai.")

    problem = invite_problem(env.get("MAIDA_INVITED_EMAILS", ""), env.get("MAIDA_ADMIN_EMAILS", ""))
    if problem:
        say(BAD, problem)
    else:
        n = len([i for i in env.get("MAIDA_INVITED_EMAILS", "").split(",") if i.strip()])
        say(OK, f"Danh sach moi: {n} muc; quan tri: {env.get('MAIDA_ADMIN_EMAILS', '').strip()}")

    if env.get("MAIDA_PAYMENTS", "").strip():
        say(BAD, "MAIDA_PAYMENTS phai de trong khi chay thu noi bo (khong ban tin dung).")
    else:
        say(OK, "Thanh toan tat.")

    if fetch_jwks and url.startswith("https://"):
        try:
            with urllib.request.urlopen(f"{url}/auth/v1/.well-known/jwks.json", timeout=10) as r:
                keys = json.load(r).get("keys", [])
            if keys:
                say(OK, f"Doc duoc khoa ky cua Supabase ({len(keys)} khoa).")
            else:
                say(WARN, "Supabase chua co khoa ky bat doi xung; neu dang nhap loi, can SUPABASE_JWT_SECRET.")
        except Exception as exc:  # network or project not reachable
            say(WARN, f"Chua doc duoc khoa ky Supabase ({exc.__class__.__name__}); kiem tra mang va SUPABASE_URL.")
    return out


def main() -> int:
    results = run(dict(os.environ))
    for level, msg in results:
        print(f"[{level}] {msg}")
    if any(level == BAD for level, _ in results):
        print("\nChua chay duoc. Sua cac dong LOI trong noi_bo.env roi chay lai.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
