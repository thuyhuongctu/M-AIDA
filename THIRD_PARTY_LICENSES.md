# THIRD_PARTY_LICENSES: Giấy phép thành phần bên thứ ba (M-AIDA v7.1.1)

M-AIDA sử dụng các thư viện và thành phần mã nguồn mở dưới đây. Bản thân các
thành phần này giữ nguyên giấy phép gốc của chúng; giấy phép của M-AIDA (xem
`LICENSE`) chỉ áp dụng cho phần mã do nhóm tác giả viết.

## 1. Thành phần chính

| Thành phần | Vai trò trong M-AIDA | Giấy phép (license) |
|---|---|---|
| FastAPI | Khung API backend | MIT |
| Pydantic | Mô hình dữ liệu và kiểm tra kiểu | MIT |
| React | Thư viện giao diện frontend | MIT |
| Vite | Công cụ build frontend | MIT |
| pytest | Khung kiểm thử backend | MIT |
| Nginx | Máy chủ phục vụ bản build frontend (Docker) | BSD-2-Clause |
| pypdfium2 | Đọc và bóc tách văn bản PDF (từ 7.1.2 trở lên; xem mục 2) | BSD-3-Clause / Apache-2.0 |

Danh sách phụ thuộc đầy đủ kèm phiên bản ghim: `backend/pyproject.toml`,
`backend/requirements.txt` và `frontend/package.json`.

## 2. Đã gỡ PyMuPDF (AGPL-3.0) khỏi phụ thuộc runtime

Bản đăng ký quyền tác giả **7.1.1** (gói lưu chiểu đã nộp, xem `IP_REGISTER.md`)
dùng **PyMuPDF**, phát hành theo giấy phép **AGPL-3.0** (copyleft mạnh): với
mục đích nghiên cứu học thuật, mã nguồn công khai như khi đó, việc này không
tạo xung đột thực tế, nhưng nếu thương mại hóa (SaaS đóng nguồn) thì toàn bộ
M-AIDA buộc phải phát hành lại theo AGPL-3.0 (xem `COMMERCIAL-LICENSE.md`).

Từ phiên bản **7.1.2 trở lên**, PyMuPDF đã được thay bằng **pypdfium2**
(BSD-3-Clause / Apache-2.0 — giấy phép dễ dãi, không copyleft) tại đúng một
điểm dùng: `backend/main.py`, hàm `extract_pdf` (tuyến `POST /api/extract`).
Việc này gỡ bỏ hoàn toàn ràng buộc AGPL khỏi phụ thuộc runtime của các phiên
bản mới, không cần chọn giữa "công bố mã nguồn" hay "mua giấy phép thương mại
PyMuPDF từ Artifex" nữa.

**Không hồi tố:** gói lưu chiểu `MAIDA_SOURCE_DEPOSIT_v7.1.1_SANITIZED.zip` đã
nộp cho Cục Bản quyền tác giả giữ nguyên, vẫn dùng PyMuPDF như đã khai trong hồ
sơ 7.1.1; thay đổi này chỉ áp dụng cho mã nguồn từ 7.1.2 trở đi, theo đúng quy
tắc "không sửa trực tiếp bản 7.1.1 đã đăng ký" tại `IP_REGISTER.md` mục 6.

## 3. Trách nhiệm cập nhật

Khi thêm hoặc nâng cấp phụ thuộc ở các phiên bản 7.1.2 trở lên, phải cập nhật
bảng này và kiểm tra tương thích giấy phép trước khi phát hành.

## Self-hosted web fonts (added 2026-08-04)

Bundled in `assets/fonts/` (woff2, latin + vietnamese subsets) and embedded
as base64 in `styleguide-standalone.html`. All three are licensed under the
SIL Open Font License 1.1, which permits bundling and redistribution:

| Font | Copyright | License |
|---|---|---|
| Source Serif 4 | Adobe Systems Incorporated | SIL OFL 1.1 |
| Inter | The Inter Project Authors (Rasmus Andersson) | SIL OFL 1.1 |
| JetBrains Mono | JetBrains s.r.o. | SIL OFL 1.1 |

Fonts are self-hosted so brand and defense pages render identically with no
CDN dependency and no third-party requests: including fully offline.
