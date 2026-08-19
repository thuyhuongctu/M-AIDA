# Trước khi công bố rộng rãi: kết quả rà 04/08/2026

Nhận định của chủ dự án là đúng: trang chưa công bố rộng rãi được. Nhưng lý do
chính **không phải lỗi câu chữ**: rà toàn bộ trang không còn TODO/DRAFT/công
thức cũ sót, mà là **thiết kế có chủ đích**: trang đang nói thật rằng số liệu
là tạm thời. Gỡ các câu đó đi để "trông sẵn sàng" là giả vờ sẵn sàng; đường
đúng là đóng Cổng 1 rồi các câu đó tự hết lý do tồn tại.

## Đã sửa ngay (lỗi thật)

- `commercial.html`: chuỗi `\n` hiển thị nguyên văn giữa hai nút
  "Try the demo" và "Defense App" (lộ trong ảnh chụp kiểm header).

## Các đoạn "đọc như chưa xong", và vì sao chúng đứng đó

| Chỗ | Nội dung | Xử lý |
|---|---|---|
| `index.html` + `docs/index.html` (3 chỗ mỗi trang) | Ghi chú "giá trị gộp hiển thị ở đây là **tạm thời**, thuộc v7.1.1, sẽ phát hành lại thành v8.0.0 kèm DOI mới" | **GIỮ**: đây là tuyên bố liêm chính, không phải câu chưa viết xong. Tự gỡ khi v8.0.0 khóa và `site-metrics.json` cập nhật. |
| `bizon.html` (2 chỗ) | "AI Advisor, coming soon", "full AI Mentor (API) coming soon" | Giữ theo danh sách đóng băng (BizOn không phát triển thêm). Nếu muốn sạch chữ "coming soon" trước công bố: đổi thành mô tả hiện trạng, một sửa chữ 5 phút, chờ chủ dự án quyết vì BizOn đang đóng băng. |
| `asia-atlas.html` | "Trang phục … đang cập nhật / render coming soon" | Trang nhận diện luận án, ngoài phạm vi công bố M-AIDA. |

## Điều kiện công bố rộng rãi (khớp Ba vòng khóa của kế hoạch hoàn thiện)

1. **Cổng 1 đóng**: v8.0.0 khóa, DOI mới phát hành, `site-metrics.json` nhận
   bộ số chính thức từ `figures.json`/metafor; ba ghi chú "tạm thời" gỡ trong
   cùng một commit với cập nhật số.
2. **PR #86 merge**: mọi thứ đã dựng (công thức đúng, cổng dẫn chứng, logo,
   giọng sạch số, demo ba bài mẫu) hiện chỉ nằm trên nhánh; web đang chạy vẫn
   là bản cũ với công thức thiếu λ.
3. **Guard xanh**: `scripts/check_site_metrics.py` đã chặn deploy khi số lệch;
   giữ nguyên cơ chế này làm cổng phát hành.
4. (Tùy chọn, 5 phút) BizOn: đổi hai câu "coming soon" thành mô tả hiện trạng.

Tóm lại: thứ tự đúng là **bảng thu hồi 47 dòng → v8.0.0 → cập nhật số + gỡ ghi
chú tạm thời → merge → công bố**, không phải sửa câu chữ trước.

## Cập nhật 04/08 (đợt 2): bốn chốt chặn mới đã cài

1. **Ghi chú tạm thời do dữ liệu điều khiển**: `site-metrics.json` mang
   `generation` + `provisional: true`; hai ghi chú trên index/docs giờ là phần
   tử `provisional-note` riêng, trang tự gỡ khi JSON đổi `provisional: false`
   (fetch lúc chạy; fetch hỏng thì ghi chú Ở LẠI, chiều an toàn).
2. **Guard chặn cả hai chiều**: provisional=true mà thiếu ghi chú → fail
   (chống gỡ non); provisional=false mà còn ghi chú → fail (chống caveat thừa).
3. **Guard bắt chuỗi thoát lọt ra HTML** (ngoài script/style), vừa cài đã bắt
   thêm một `\n` thứ hai trên commercial.html mà mắt bỏ sót; đã sửa cả hai.
4. **Guard bắt dấu phẩy thập phân trong chuỗi tiếng Việt** (quy tắc xuất xứ,
   THUAT_NGU §4); toàn bộ data-vi đã chuyển về dấu chấm, kèm câu quy ước đặt
   một lần ở chú thích biểu đồ rừng.

BizOn: hai câu "coming soon" (EN+VI) đã đổi thành mô tả hiện trạng, sửa câu
chữ, không phải phát triển thêm, không vi phạm đóng băng.

## Xếp sau Cổng 1: viết lại bản tiếng Việt như bản gốc

Theo `THUAT_NGU_VA_QUY_TAC_TIENG_VIET.md` (đã đưa vào kho): viết lại toàn bộ
data-vi như bản gốc song song (tiêu đề viết lại không dịch; tách câu; bớt
«việc/được»; thống nhất bảng thuật ngữ; xử lý eyebrow chữ hoa có dấu). Công
việc vài buổi, không chặn Cổng 1, không làm trước Cổng 1.
