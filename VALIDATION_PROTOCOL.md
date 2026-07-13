# VALIDATION_PROTOCOL: Quy trình đánh giá hiệu năng trích xuất (M-AIDA v7.1.1)

Quy trình chuẩn hóa để lượng hóa chất lượng trích xuất của M-AIDA trên bộ
chuẩn vàng do con người lập, nhằm chuyển các tuyên bố về hiệu quả thành bằng
chứng kiểm chứng được. Kết quả sẽ báo cáo trong `VALIDATION_REPORT.md` và
tiểu mục validation của Phụ lục B luận án.

## 1. Mẫu đánh giá (Benchmark sample)

- Quy mô: **30 đến 50 bài** chọn từ bộ nghiên cứu P6.
- Lấy mẫu **phân tầng** theo dạng báo cáo thống kê và độ khó, bao phủ:
  1. bài chỉ báo cáo hệ số r;
  2. bài báo cáo t, F, p hoặc khoảng tin cậy (cần quy đổi);
  3. bài báo cáo beta chuẩn hóa;
  4. bài có nhiều mức độ ảnh hưởng trong cùng một bài;
  5. bài có bảng phức tạp;
  6. bản scan cũ, chất lượng thấp;
  7. bài đa quốc gia hoặc đa thời kỳ.

## 2. Chuẩn vàng (Gold standard)

- Nghiên cứu sinh mã hóa lần một toàn bộ mẫu bằng tay từ toàn văn.
- Một người kiểm tra **độc lập** mã hóa lại hoặc rà soát toàn bộ.
- Bất đồng giải quyết bằng đối chiếu trực tiếp với toàn văn; giá trị đồng
  thuận là chuẩn vàng.

## 3. Chỉ tiêu đo (Metrics)

| Chỉ tiêu | Nội dung |
|---|---|
| Precision, Recall, F1 | Nhận diện đúng đại lượng thống kê trọng tâm |
| Accuracy của r | Tỷ lệ khớp giá trị r (exact match theo dung sai làm tròn của bài gốc) |
| Accuracy của dấu | Tỷ lệ đúng dấu (âm/dương) của hệ số |
| MAE chuyển đổi | Sai số tuyệt đối trung bình của giá trị r quy đổi từ t, F, beta |
| Tỷ lệ ghi đè | Tỷ lệ trường bị PI sửa hoặc ghi đè khi xác minh |
| Tỷ lệ hallucination | Tỷ lệ giá trị máy đề xuất không tồn tại trong tài liệu nguồn |
| Cohen's kappa | Độ nhất trí cho các biến phân loại |
| Thời gian mỗi bài | Thời gian xử lý và xác minh trung bình trên một bài |

## 4. Ngưỡng quản trị nội bộ (Internal governance thresholds)

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

## 5. Điều kiện tái lập

- Phần mềm: M-AIDA phiên bản 7.1.1 (bản chuẩn tham chiếu, đóng băng).
- Ghi lại nhà cung cấp mô hình, mã mô hình, phiên bản prompt, temperature,
  ngày trích xuất và người xác minh vào `REPRODUCIBILITY_MANIFEST.json`
  cho từng đợt chạy.
- Phân tích thống kê của benchmark thực hiện ngoài M-AIDA và lưu kèm script.

## 6. Đầu ra

1. `VALIDATION_REPORT.md`: số liệu thật trên toàn bộ chỉ tiêu, kèm mô tả mẫu
   và quy trình giải quyết bất đồng.
2. Cập nhật tiểu mục validation trong Phụ lục B của luận án, dẫn kết quả từ
   báo cáo trên.
