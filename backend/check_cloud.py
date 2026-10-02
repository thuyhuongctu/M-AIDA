"""Kiểm tra cấu hình cloud (deploy/.env.cloud) trước khi mở dịch vụ 8.x.

Chạy trên máy chủ, trước `docker compose up`:

    docker compose -f docker-compose.cloud.yml --env-file deploy/.env.cloud \
        run --rm --no-deps backend python check_cloud.py

hoặc tại máy phát triển với tệp cấu hình chỉ định:

    python backend/check_cloud.py --env deploy/.env.cloud

Từng mục in ĐẠT / HỎNG kèm cách sửa. Không in bí mật (khóa, mật khẩu) ra
màn hình: chỉ 4 ký tự cuối của khóa mô hình và tên máy chủ Postgres.
Mã thoát 0 khi mọi mục bắt buộc đạt; 1 khi có mục hỏng.

Các mục:
  1. MAIDA_AUTH_MODE và các biến bắt buộc cho chế độ đó.
  2. Postgres: kết nối được, phiên bản, và lược đồ Alembic (đã ở head hay sẽ
     được nâng khi backend khởi động).
  3. Supabase Auth: JWKS tải được (khóa bất đối xứng) hoặc có SUPABASE_JWT_SECRET.
  4. Mô hình: một yêu cầu 5 token tới LLM_MODEL (bỏ qua với --no-llm).
  5. Cảnh báo: chế độ mock, demo bật, thiếu MAIDA_ADMIN_EMAILS, CORS.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OK, BAD, WARN = "ĐẠT ", "HỎNG", "LƯU Ý"


def say(tag: str, text: str) -> None:
    print(f"[check_cloud] {tag}  {text}", flush=True)


def load_env_file(path: str) -> None:
    """Minimal .env loader (KEY=VALUE, # comments, optional quotes); does not override exported vars."""
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.split(" #", 1)[0].strip()  # trailing inline comment
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)


def check_db(url: str) -> bool:
    from sqlalchemy import text

    from db import make_engine

    safe = url.split("@")[-1] if "@" in url else url
    try:
        engine = make_engine(url)
        with engine.connect() as conn:
            version = conn.execute(text("select version()")).scalar() if url.startswith("postgres") else "sqlite"
            try:
                head = conn.execute(text("select version_num from alembic_version")).scalar()
            except Exception:  # noqa: BLE001 - table absent on a fresh database
                head = None
        engine.dispose()
    except Exception as exc:  # noqa: BLE001 - show the driver's message
        say(BAD, f"Postgres: không kết nối được tới {safe}: {str(exc)[:300]}")
        print("     -> Kiểm tra DATABASE_URL (Project Settings → Database → Connection string, Transaction pooler,"
              " cổng 6543), mật khẩu CSDL, và firewall. Mật khẩu có ký tự đặc biệt phải mã hóa URL (ví dụ @ → %40).")
        return False
    say(OK, f"Postgres: kết nối {safe} ({str(version)[:40]})")
    if head:
        say(OK, f"Lược đồ: Alembic ở bản {head}")
    else:
        say(WARN, "Lược đồ: chưa có bảng; backend sẽ chạy `alembic upgrade head` khi khởi động lần đầu.")
    return True


def check_auth(settings) -> bool:
    mode = settings.maida_auth_mode
    if mode == "admin_key":
        say(WARN, "MAIDA_AUTH_MODE=admin_key: chế độ một người vận hành, không có đăng nhập người dùng. "
                  "Dịch vụ nhiều người dùng cần MAIDA_AUTH_MODE=supabase.")
        return True
    if mode == "mock":
        say(BAD, "MAIDA_AUTH_MODE=mock: token ký cục bộ, chỉ để kiểm thử. KHÔNG mở ra Internet với chế độ này.")
        return False
    if mode != "supabase":
        say(BAD, f"MAIDA_AUTH_MODE={mode!r} không hợp lệ (admin_key | supabase | mock).")
        return False
    ok = True
    if not settings.supabase_url:
        say(BAD, "SUPABASE_URL trống (Project Settings → API → Project URL).")
        ok = False
    if not settings.supabase_anon_key:
        say(BAD, "SUPABASE_ANON_KEY trống (Project Settings → API Keys → publishable/anon); giao diện cần để đăng nhập.")
        ok = False
    if settings.supabase_jwks_url:
        try:
            with urllib.request.urlopen(settings.supabase_jwks_url, timeout=10) as r:
                keys = json.load(r).get("keys", [])
        except (urllib.error.URLError, ValueError, OSError) as exc:
            say(BAD, f"JWKS: không tải được {settings.supabase_jwks_url}: {exc}")
            ok = False
            keys = None
        if keys:
            algs = sorted({k.get("alg", "?") for k in keys})
            say(OK, f"JWKS: {len(keys)} khóa ({', '.join(algs)}); backend xác minh token bằng khóa công khai.")
        elif keys is not None:
            if settings.supabase_jwt_secret:
                say(OK, "JWKS rỗng (dự án còn dùng JWT secret HS256) và SUPABASE_JWT_SECRET đã có.")
            else:
                say(BAD, "JWKS rỗng: dự án ký token bằng secret HS256 nhưng SUPABASE_JWT_SECRET trống. "
                         "Lấy ở Project Settings → JWT Keys (Legacy JWT secret), hoặc chuyển dự án sang JWT Signing Keys.")
                ok = False
    if not settings.admin_emails:
        say(WARN, "MAIDA_ADMIN_EMAILS trống: sẽ không có tài khoản admin để cấp tín dụng.")
    return ok


def check_llm(settings) -> bool:
    key = settings.anthropic_api_key
    if not key:
        say(BAD, "LLM_API_KEY trống: mọi lượt trích xuất sẽ trả 503.")
        return False
    from engines import AnthropicEngine

    model = settings.resolved_model or AnthropicEngine.DEFAULT_MODEL
    try:
        engine = AnthropicEngine(api_key=key, model=model)
        reply = engine.complete(system="Reply with the single word OK.", user="ping", max_tokens=5)
    except Exception as exc:  # noqa: BLE001 - show the provider's message
        say(BAD, f"Mô hình {model} (khóa ...{key[-4:]}): {str(exc)[:300]}")
        print("     -> Xem backend/check_llm.py để biết cách sửa theo từng loại lỗi (mã mô hình, khóa, hạn mức).")
        return False
    usage = engine.last_usage or {}
    say(OK, f"Mô hình {model} trả lời {reply.strip()[:20]!r}; usage {usage.get('input_tokens', '?')} vào / "
            f"{usage.get('output_tokens', '?')} ra; khóa ...{key[-4:]}")
    if not settings.resolved_model:
        say(WARN, "LLM_MODEL trống: đang dùng mặc định của adapter. Ghim rõ LLM_MODEL để nghiên cứu đánh giá có giá trị.")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--env", default="", help="đường dẫn tệp .env (mặc định: biến môi trường hiện có / backend/.env)")
    ap.add_argument("--no-llm", action="store_true", help="bỏ qua lời gọi mô hình")
    args = ap.parse_args(argv)
    if args.env:
        if not os.path.isfile(args.env):
            say(BAD, f"Không thấy tệp {args.env}")
            return 1
        load_env_file(args.env)

    import settings as settings_module

    settings_module._settings = None
    settings = settings_module.get_settings()

    say(OK if settings.maida_auth_mode == "supabase" else WARN, f"MAIDA_AUTH_MODE={settings.maida_auth_mode}")
    results = [check_auth(settings)]
    url = settings.resolved_database_url
    if url.startswith("sqlite"):
        say(WARN, f"DATABASE_URL trống: dùng SQLite tại {settings.maida_db_path}. Dịch vụ nhiều người dùng nên dùng Postgres.")
        results.append(check_db(url))
    else:
        results.append(check_db(url))
    if settings.maida_demo_mode:
        say(BAD, "MAIDA_DEMO_MODE=true: chế độ demo tắt khóa quản trị; phải là false khi mở dịch vụ.")
        results.append(False)
    if not args.no_llm:
        results.append(check_llm(settings))
    if all(results):
        say(OK, "Mọi mục bắt buộc đạt. Có thể chạy docker compose up.")
        return 0
    say(BAD, "Có mục hỏng ở trên; sửa rồi chạy lại.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
