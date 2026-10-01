"""Kiểm tra mã khoá và mã mô hình trong backend/.env trước khi trích xuất thật.

Chạy từ thư mục gốc kho (hoặc từ CHAY_MAIDA_WINDOWS.bat):

    .venv\\Scripts\\python.exe backend\\check_llm.py

Gửi một yêu cầu rất nhỏ (tối đa 5 token) tới mô hình đang cấu hình và in kết
quả. Mục đích: nếu mã khoá sai, hết hạn mức, hoặc mã mô hình trong LLM_MODEL
không tồn tại, cô biết ngay ở đây thay vì thấy mọi lượt tải PDF đều hỏng với
một thông báo khó hiểu. Không in mã khoá ra màn hình.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from settings import get_settings  # noqa: E402

settings = get_settings()


def main() -> int:
    key = settings.anthropic_api_key
    if not key:
        print("[check_llm] Chưa có LLM_API_KEY trong backend/.env. Chạy CHAY_MAIDA_WINDOWS.bat để nhập, hoặc tự thêm dòng LLM_API_KEY=sk-ant-...")
        return 2
    from engines import AnthropicEngine

    model = settings.resolved_model or AnthropicEngine.DEFAULT_MODEL
    print(f"[check_llm] Khoá: ...{key[-4:]} (chỉ hiện 4 ký tự cuối). Mô hình: {model}")
    try:

        engine = AnthropicEngine(api_key=key, model=model)
        reply = engine.complete(system="Reply with the single word OK.", user="ping", max_tokens=5)
    except Exception as exc:  # noqa: BLE001 - we want the raw provider message here
        msg = str(exc)
        print(f"[check_llm] THẤT BẠI: {msg[:400]}")
        low = msg.lower()
        if "not_found" in low or "model" in low and "not found" in low:
            print("  -> Mã mô hình trong LLM_MODEL không tồn tại với tài khoản này. Sửa LLM_MODEL trong backend/.env "
                  "theo danh sách tại https://docs.claude.com/en/docs/about-claude/models rồi chạy lại.")
        elif "authentication" in low or "invalid x-api-key" in low or "401" in low:
            print("  -> Mã khoá sai hoặc đã bị thu hồi. Tạo mã mới tại https://console.anthropic.com/settings/keys.")
        elif "credit" in low or "billing" in low or "quota" in low or "429" in low:
            print("  -> Tài khoản hết hạn mức hoặc chưa nạp tiền; kiểm tra mục Billing/Limits trên console.anthropic.com.")
        return 1
    print(f"[check_llm] THÀNH CÔNG. Mô hình trả lời: {reply.strip()[:40]!r}. Có thể trích xuất thật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
