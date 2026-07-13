# IP_REGISTER: Bản ghi quản trị sở hữu trí tuệ (M-AIDA)

Tài liệu quản trị nội bộ, ghi nhận hiện trạng sở hữu trí tuệ (SHTT) của phần mềm
M-AIDA. Tài liệu này KHÔNG thay thế các văn bản đã nộp trong hồ sơ đăng ký quyền
tác giả; khi có khác biệt, văn bản đã nộp chính thức là căn cứ pháp lý.

## 1. Định danh tác phẩm (Work identification)

| Khóa (Key) | Giá trị |
|---|---|
| Tên tác phẩm (title) | M-AIDA (Meta-Analysis Intelligent Data Assistant) |
| Loại hình (type) | Chương trình máy tính (computer software) |
| Phiên bản đăng ký (registered version) | 7.1.1 |
| Ngày phát hành 7.1.1 (release date) | 09/07/2026 |
| Kho mã nguồn (repository) | https://github.com/thuyhuongctu/M-AIDA |
| DOI Zenodo, concept (mọi phiên bản) | 10.5281/zenodo.21282516 |
| DOI Zenodo, version (bản v7.1.1) | 10.5281/zenodo.21282517 |
| Giấy phép phân phối (license) | M-AIDA Academic Source-Available License v1.0 (xem `LICENSE`) |

## 2. Tác giả (Authors)

1. **Đỗ Thùy Hương**, nghiên cứu sinh ngành Quản trị kinh doanh, Trường Kinh tế,
   Trường Đại học Cần Thơ; ORCID 0000-0002-7711-2487.
2. **PGS.TS. Phan Anh Tú**, giảng viên cao cấp, Trường Kinh tế, Trường Đại học
   Cần Thơ; ORCID 0000-0003-0667-3137.

Phân công vai trò chi tiết: xem `AUTHORS_AND_OWNERSHIP.md`.

## 3. Hồ sơ đăng ký quyền tác giả (Copyright registration)

- Hình thức: **đồng sở hữu** giữa Trường Đại học Cần Thơ và hai tác giả, theo
  Điều 71 Quy chế quản lý hoạt động khoa học và công nghệ (Quyết định số
  5152/QĐ-ĐHCT ngày 06/10/2023).
- Kênh nộp: hồ sơ nộp qua Trường Đại học Cần Thơ; đầu mối là Phòng Khoa học,
  Công nghệ và Đổi mới Sáng tạo (Phòng KHCN); nơi tiếp nhận cuối là Cục Bản
  quyền tác giả (Bộ Văn hóa, Thể thao và Du lịch).
- Bộ hồ sơ và các văn bản kèm theo: xem `p6/submission/maida_copyright/`
  (trong kho luận án) gồm đơn đề nghị, tờ khai Mẫu số 03, bản mô tả chương
  trình, bản in mã nguồn, văn bản đồng ý đồng tác giả, thư gửi Trường và
  checklist nộp.

## 4. Gói lưu chiểu mã nguồn (Source deposit)

| Khóa (Key) | Giá trị |
|---|---|
| Tên gói | `MAIDA_SOURCE_DEPOSIT_v7.1.1_SANITIZED.zip` |
| SHA-256 | `43a5d77296757fdd3cdf5c40e585bebcf05f3c9889d7f0dda41b75cd8d9ab9b5` |
| Nội dung | 41 tệp, trong đó 17 tệp mã nguồn; đã loại bỏ mọi khóa bí mật (sanitized) |
| Tệp mã băm | `MAIDA_SOURCE_DEPOSIT_v7.1.1_SANITIZED.sha256.txt` (cùng thư mục hồ sơ) |

## 5. Ghi chú đối chiếu phiên bản (Version reconciliation note)

Ghi chú này lập ra để hội đồng và cơ quan đăng ký không hiểu nhầm là hồ sơ
mâu thuẫn:

1. **Bản mô tả chương trình đã nộp** ghi phiên bản **7.1.0** (33 tệp, 4.397
   dòng mã, cấu trúc lõi hoàn thành ngày 08/6/2026).
2. **Gói mã nguồn hoàn chỉnh nộp bổ sung** theo thư ngày **12/07/2026** là
   phiên bản **7.1.1** (41 tệp, trong đó 17 tệp mã nguồn).
3. Quan hệ giữa hai phiên bản: **7.1.1 là bản vá hoàn thiện của 7.1.0**, bổ
   sung một tệp giao diện còn thiếu để chương trình biên dịch đầy đủ; kiến
   trúc, chức năng và mục đích của tác phẩm không thay đổi.
4. Các văn bản khác trong hồ sơ (đơn đề nghị, tờ khai, văn bản đồng ý đồng
   tác giả, thỏa thuận đồng sở hữu) **giữ nguyên**, không phải nộp lại.

## 6. Quy tắc sau đóng băng (Post-freeze rules)

- **Không sửa trực tiếp** mã nguồn, kiến trúc, chức năng hay giao diện của bản
  7.1.1 đã đăng ký (Registered Reference Release).
- Mọi thay đổi đi vào các phiên bản **7.1.2 trở lên hoặc 7.2** theo Semantic
  Versioning: 7.1.2 chỉ sửa lỗi; 7.2.0 thêm chức năng nhưng giữ kiến trúc và
  mục đích; 8.0.0 thay đổi lớn về kiến trúc hoặc phạm vi.
- **Đăng ký bổ sung SHTT** cho phiên bản mới chỉ thực hiện khi phiên bản đó có
  thay đổi sáng tạo đáng kể, và chỉ sau khi tham vấn chuyên gia SHTT; nhóm tác
  giả không tự khẳng định phạm vi bảo hộ.

## 7. Nhật ký cập nhật bản ghi này

| Ngày | Nội dung |
|---|---|
| 13/07/2026 | Lập bản ghi; ấn định 7.1.1 là bản chuẩn tham chiếu đã đăng ký; ghi chú đối chiếu 7.1.0/7.1.1 |

## Định danh commit của bản chuẩn tham chiếu (bổ sung 13/07/2026)

- Commit trùng khớp gói nộp SHTT: `24dac0219b8020bd8f0b1c7d048f7a9ee9340dfe`
  (đối chiếu checksum: 17 tệp mã nguồn trùng 100% với gói SANITIZED; khác biệt duy nhất
  là README.md, thuộc tài liệu mô tả, không phải mã nguồn đăng ký).
- Trạng thái tag: tag `v7.1.1` hiện có trên GitHub trỏ vào commit `93e38a4` (trước đợt
  trung lập hóa nhà cung cấp) nên KHÔNG dùng làm bản tham chiếu. Chủ sở hữu cần cập nhật
  tag bằng hai lệnh sau trên máy có quyền đẩy tag:
  `git tag -fa v7.1.1 24dac0219b8020bd8f0b1c7d048f7a9ee9340dfe -m "Registered Reference Release"`
  `git push --force origin v7.1.1`
  Sau đó tạo GitHub Release "M-AIDA v7.1.1 - Registered Reference Release" từ tag này,
  dán SHA-256 của gói nộp vào phần ghi chú release.
