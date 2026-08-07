# Trước khi công bố rộng rãi — kết quả rà 04/08/2026

Nhận định của chủ dự án là đúng: trang chưa công bố rộng rãi được. Nhưng lý do
chính **không phải lỗi câu chữ** — rà toàn bộ trang không còn TODO/DRAFT/công
thức cũ sót — mà là **thiết kế có chủ đích**: trang đang nói thật rằng số liệu
là tạm thời. Gỡ các câu đó đi để "trông sẵn sàng" là giả vờ sẵn sàng; đường
đúng là đóng Cổng 1 rồi các câu đó tự hết lý do tồn tại.

## Đã sửa ngay (lỗi thật)

- `commercial.html`: chuỗi `\n` hiển thị nguyên văn giữa hai nút
  "Try the demo" và "Defense App" (lộ trong ảnh chụp kiểm header).

## Các đoạn "đọc như chưa xong" — và vì sao chúng đứng đó

| Chỗ | Nội dung | Xử lý |
|---|---|---|
| `index.html` + `docs/index.html` (3 chỗ mỗi trang) | Ghi chú "giá trị gộp hiển thị ở đây là **tạm thời**, thuộc v7.1.1, sẽ phát hành lại thành v8.0.0 kèm DOI mới" | **GIỮ** — đây là tuyên bố liêm chính, không phải câu chưa viết xong. Tự gỡ khi v8.0.0 khóa và `site-metrics.json` cập nhật. |
| `bizon.html` (2 chỗ) | "AI Advisor — coming soon", "full AI Mentor (API) coming soon" | Giữ theo danh sách đóng băng (BizOn không phát triển thêm). Nếu muốn sạch chữ "coming soon" trước công bố: đổi thành mô tả hiện trạng, một sửa chữ 5 phút — chờ chủ dự án quyết vì BizOn đang đóng băng. |
| `asia-atlas.html` | "Trang phục … đang cập nhật / render coming soon" | Trang nhận diện luận án, ngoài phạm vi công bố M-AIDA. |

## Điều kiện công bố rộng rãi (khớp Ba vòng khóa của kế hoạch hoàn thiện)

1. **Cổng 1 đóng** — v8.0.0 khóa, DOI mới phát hành, `site-metrics.json` nhận
   bộ số chính thức từ `figures.json`/metafor; ba ghi chú "tạm thời" gỡ trong
   cùng một commit với cập nhật số.
2. **PR #86 merge** — mọi thứ đã dựng (công thức đúng, cổng dẫn chứng, logo,
   giọng sạch số, demo ba bài mẫu) hiện chỉ nằm trên nhánh; web đang chạy vẫn
   là bản cũ với công thức thiếu λ.
3. **Guard xanh** — `scripts/check_site_metrics.py` đã chặn deploy khi số lệch;
   giữ nguyên cơ chế này làm cổng phát hành.
4. (Tùy chọn, 5 phút) BizOn: đổi hai câu "coming soon" thành mô tả hiện trạng.

Tóm lại: thứ tự đúng là **bảng thu hồi 47 dòng → v8.0.0 → cập nhật số + gỡ ghi
chú tạm thời → merge → công bố**, không phải sửa câu chữ trước.
