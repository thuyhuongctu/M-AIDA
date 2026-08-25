# VALIDATION_PROTOCOL: Quy trình đánh giá hiệu năng trích xuất (M-AIDA v7.1.1)

Quy trình chuẩn hóa để lượng hóa chất lượng trích xuất của M-AIDA trên bộ
chuẩn vàng do con người lập, nhằm chuyển các tuyên bố về hiệu quả thành bằng
chứng kiểm chứng được. Kết quả sẽ báo cáo trong `VALIDATION_REPORT.md` và
tiểu mục validation của Phụ lục B luận án.

## 1. Thiết kế độc lập và chống vòng lặp

- Đóng băng trước phiên bản M-AIDA, prompt, mô hình và ngưỡng đánh giá; không
  điều chỉnh sau khi xem kết quả.
- Đơn vị lấy mẫu là **candidate effect**, gồm cả trường hợp có và không phải
  hệ số focal internationalization-performance. Nhờ vậy precision và
  hallucination có mẫu số thực, không chỉ đo trên các trường hợp đã biết là đúng.
- Hai người mã hóa chuẩn vàng không xem đề xuất M-AIDA trước khi hoàn tất lần
  mã hóa đầu. Lưu riêng quyết định trước phân xử của từng người.
- Dữ liệu demo, unit-test fixture và các bản ghi từng dùng để chỉnh prompt
  không được đưa vào mẫu kiểm định độc lập.
- M-AIDA chỉ được đánh giá ở khâu chuẩn bị effect-size data. Protocol này
  không kiểm định screening, risk-of-bias, mô hình meta-analysis hay diễn giải P6.

## 2. Mẫu đánh giá (Benchmark sample)

- Quy mô: **30 đến 50 bài**, lấy từ full-text corpus P6 đã hoàn tất tiêu chí
  chọn nghiên cứu nhưng chưa được dùng để phát triển/tinh chỉnh M-AIDA.
- Lấy mẫu **phân tầng** theo dạng báo cáo thống kê và độ khó, bao phủ:
  1. bài chỉ báo cáo hệ số r;
  2. bài báo cáo t, F, p hoặc khoảng tin cậy (cần quy đổi);
  3. bài báo cáo beta chuẩn hóa;
  4. bài có nhiều mức độ ảnh hưởng trong cùng một bài;
  5. bài có bảng phức tạp;
  6. bản scan cũ, chất lượng thấp;
  7. bài đa quốc gia hoặc đa thời kỳ.

Mỗi bài phải có ít nhất một candidate effect; bổ sung các hệ số kiểm soát,
tương tác hoặc kết quả không focal để kiểm tra khả năng chọn đúng hệ số.

## 3. Chuẩn vàng (Gold standard)

- Nghiên cứu sinh mã hóa lần một toàn bộ mẫu bằng tay từ toàn văn.
- Người thứ hai **độc lập** mã hóa lại toàn bộ, bị làm mù với đề xuất của
  M-AIDA và quyết định của người thứ nhất.
- Bất đồng giải quyết bằng đối chiếu trực tiếp với toàn văn; giá trị đồng
  thuận là chuẩn vàng.
- Mọi trường hợp ghi `case_id`, vị trí nguồn (trang/bảng/dòng), thời gian mã
  hóa và ghi chú phân xử bằng `validation/gold_standard_template.csv`.

## 4. Chỉ tiêu đo (Metrics)

| Chỉ tiêu | Nội dung |
|---|---|
| Precision, Recall, F1 | Nhận diện đúng đại lượng thống kê trọng tâm |
| Accuracy của r | Tỷ lệ khớp giá trị r (dung sai khóa trước, mặc định ±0,005) |
| Accuracy của dấu | Tỷ lệ đúng dấu (âm/dương) của hệ số |
| MAE chuyển đổi | Sai số tuyệt đối trung bình của giá trị r quy đổi từ t, F, beta |
| Tỷ lệ ghi đè | Tỷ lệ machine proposal cần PI sửa ít nhất một trường |
| Tỷ lệ hallucination | Tỷ lệ machine proposal không tồn tại trong tài liệu nguồn |
| Provenance completeness | Tỷ lệ đề xuất có vị trí nguồn kiểm tra được |
| Cohen's kappa | Độ nhất trí giữa hai người mã hóa trước phân xử |
| Thời gian | So sánh cặp thời gian mã hóa thủ công và xác minh có M-AIDA |

Báo cáo thêm kết quả theo tuyến `direct_r`, `t_to_r`, `beta_to_r` và nhóm
khác; không gộp các tuyến để che giấu sai số chuyển đổi.

## 5. Ngưỡng quản trị nội bộ (Internal governance thresholds)

Các ngưỡng dưới đây là **chuẩn quản trị nội bộ** của dự án, KHÔNG phải chuẩn
phổ quát của lĩnh vực; nêu rõ điều này trong mọi báo cáo:

| Chỉ tiêu | Ngưỡng |
|---|---|
| Sai dấu ở bản ghi đã khóa | 0% |
| Hallucination sau xác minh (trong dữ liệu đã khóa) | 0% |
| Provenance completeness (bản ghi truy ngược được về nguồn) | 100% |
| Exact-match giá trị r | >= 95% |
| F1 phân loại | >= 0,90 |

Nếu kết quả thấp hơn ngưỡng: báo cáo trung thực, phân tích nguyên nhân và ghi
vào phần hạn chế; không điều chỉnh ngưỡng hồi tố, không loại bỏ trường hợp
bất lợi.

## 6. Điều kiện tái lập

- Phần mềm: M-AIDA phiên bản 7.1.1 (bản chuẩn tham chiếu, đóng băng).
- Ghi lại nhà cung cấp mô hình, mã mô hình, phiên bản prompt, temperature,
  ngày trích xuất và người xác minh vào `REPRODUCIBILITY_MANIFEST.json`
  cho từng đợt chạy.
- Phân tích benchmark thực hiện ngoài M-AIDA bằng
  `validation/analyze_validation.py`; script chỉ dùng Python standard library.
- Lưu checksum và archive hai tệp input, JSON metrics, báo cáo Markdown, commit
  SHA và ngày chạy. Unit tests của script không phải kết quả validation.

## 7. Trình tự thực hiện

1. Khóa sampling frame và tạo `case_id` trước khi chạy M-AIDA.
2. Hai coder hoàn tất độc lập, sau đó phân xử thành gold standard.
3. Chạy đúng một cấu hình M-AIDA đã khóa; giữ nguyên machine proposal.
4. PI xác minh đề xuất và ghi số trường sửa cùng thời gian.
5. Chạy script độc lập, không xóa trường hợp bất lợi và công bố toàn bộ mẫu số.
6. Chỉ sau bước 5 mới đối chiếu với ngưỡng quản trị đã đăng ký trước.

## 8. Đầu ra

1. `validation/results/VALIDATION_REPORT.md`: số liệu thật trên toàn bộ chỉ
   tiêu, kèm mô tả mẫu và quy trình giải quyết bất đồng.
2. `validation/results/validation_metrics.json`: kết quả máy đọc được.
3. Cập nhật tiểu mục validation trong Phụ lục B của luận án, dẫn kết quả từ
   báo cáo trên.

**Trạng thái hiện tại:** protocol, mã phân tích và sampling frame sơ bộ gồm 40
bài chính + 10 bài dự phòng đã sẵn sàng. Sampling frame vẫn `PROVISIONAL` cho
đến khi xác nhận đủ full text và không có bài nào từng dùng để phát triển hoặc
tinh chỉnh M-AIDA. Kiểm định độc lập chưa hoàn tất, vì vậy chưa có tuyên bố
accuracy/efficiency của M-AIDA.
