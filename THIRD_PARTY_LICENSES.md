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
| PyMuPDF | Đọc và bóc tách văn bản PDF | AGPL-3.0 (có tùy chọn giấy phép thương mại từ Artifex) |

Danh sách phụ thuộc đầy đủ kèm phiên bản ghim: `backend/pyproject.toml`,
`backend/requirements.txt` và `frontend/package.json`.

## 2. Lưu ý riêng về PyMuPDF (AGPL-3.0)

PyMuPDF phát hành theo giấy phép **AGPL-3.0**, là giấy phép copyleft mạnh:

- Với mục đích **nghiên cứu học thuật, minh bạch và kiểm chứng** như hiện nay
  (mã nguồn M-AIDA đã công khai trên GitHub), việc sử dụng PyMuPDF không tạo
  ra xung đột thực tế vì mã nguồn đã được cung cấp công khai.
- Khi **thương mại hóa** M-AIDA (bán bản quyền, cung cấp dịch vụ SaaS đóng
  nguồn), nghĩa vụ AGPL-3.0 cần được rà soát lại: hoặc công bố mã nguồn của
  bản phân phối theo điều kiện AGPL, hoặc mua giấy phép thương mại PyMuPDF
  từ Artifex, hoặc thay thế PyMuPDF bằng thư viện đọc PDF có giấy phép rộng
  hơn. Việc rà soát này phải thực hiện cùng chuyên gia pháp lý trước khi
  thương mại hóa.

## 3. Trách nhiệm cập nhật

Khi thêm hoặc nâng cấp phụ thuộc ở các phiên bản 7.1.2 trở lên, phải cập nhật
bảng này và kiểm tra tương thích giấy phép trước khi phát hành.
