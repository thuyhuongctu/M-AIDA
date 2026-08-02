# Đặc tả M-AIDA 7.2 (bản thiết kế, chưa lập trình)

**Trạng thái:** thiết kế cho chương trình nghiên cứu kế tiếp sau luận án. Bản 7.1.1
(Registered Reference Release) được đóng băng; mọi thay đổi dưới đây chỉ triển khai
trên nhánh 7.2, giữ nguyên mục đích cốt lõi: trợ lý quản trị dữ liệu cho phân tích
tổng hợp, con người quyết định cuối cùng, không thực hiện ước lượng thống kê bên trong.

## Nguyên tắc thiết kế

1. Tương thích ngược: dữ liệu 7.1.1 đọc được trong 7.2 mà không chuyển đổi phá hủy.
2. Mọi trường mới đều phục vụ truy vết nguồn gốc hoặc kiểm soát chất lượng.
3. Semantic Versioning: 7.2.0 thêm chức năng, không đổi kiến trúc FastAPI + React.

## Tám chức năng (thứ tự ưu tiên)

### F1. Source-grounded extraction (trích xuất neo nguồn)
Mỗi trường dữ liệu do máy đề xuất kèm: số trang, chỉ mục đoạn hoặc bảng, tọa độ
khung chữ nhật trên trang (x, y, w, h theo PyMuPDF), và trích đoạn văn bản nguồn.
Mô hình dữ liệu: thêm `SourceAnchor {page:int, kind:paragraph|table|figure, bbox:[f,f,f,f], quote:str}`
gắn theo từng trường trong `ExtractionResult`. API: mở rộng payload của POST /api/extract.
Giao diện: nhấp vào trường trong VerificationPanel làm nổi vùng nguồn trên bản xem PDF.

### F2. Confidence theo từng trường
Thay một điểm tin cậy chung bằng `field_confidence: dict[str, float]` cho r, n, thống kê
nguồn, quốc gia, năm, thước đo. Quy tắc gán giữ ba bậc 1,0/0,8/0,6 cho tuyến chuyển đổi,
cộng thêm điểm nhận diện theo trường. Ngưỡng gắn cờ 0,70 áp theo trường, không theo bản ghi.

### F3. Double verification (kiểm tra kép)
Vòng đời trạng thái mở rộng: machine_extracted -> pi_verified -> second_reviewer_verified -> locked.
Trường mới: `second_reviewer`, `second_verified_at`, `adjudication_note` (bắt buộc khi hai
người kiểm khác nhau). Cấu hình cho phép bật/tắt bước hai (mặc định tắt để tương thích 7.1.1).

### F4. Duplicate detection
Khóa mờ: DOI chuẩn hóa; nếu thiếu DOI thì bộ (tác giả chuẩn hóa, năm, tiêu đề rút gọn,
khoảng thời kỳ mẫu, quốc gia). Cảnh báo ở giao diện trước khi khóa; nhật ký cặp nghi trùng
xuất được thành `duplicates_review.csv`.

### F5. Formula registry
Bảng đăng ký công thức chuyển đổi: mã công thức, biểu thức, nguồn tham khảo (Cohen 1988;
Peterson và Brown 2005; bổ sung d sang r, OR sang r khi có kiểm định), đầu vào, đầu ra,
phiên bản. Mỗi bản ghi tham chiếu mã công thức thay vì chuỗi tự do.

### F6. Prompt registry
Mỗi lần trích xuất lưu `prompt_version`, `prompt_hash`, `model_provider`, `model_identifier`
(theo cấu hình runtime của người dùng), `temperature`. Xuất kèm trong manifest tái lập.

### F7. Schema gate trước khi khóa
Không cho phép khóa nếu thiếu: r hợp lệ trong khoảng đơn vị, n, tuyến chuyển đổi, neo nguồn
(F1), ghi chú xác minh. Thông báo lỗi liệt kê đúng trường thiếu.

### F8. PRISMA exclusion log
Ghi lý do loại ở cấp toàn văn theo bộ mã (không trích được thống kê, trùng lặp, ngoài phạm
vi, chất lượng bản chụp), xuất `prisma_exclusions.csv` để dựng flow diagram PRISMA 2020.

## Ngoài phạm vi 7.2 (giữ nguyên ranh giới)

Không ước lượng meta-analysis trong hệ thống; không tự quyết định inclusion; không risk-of-bias
tự động (thuộc 8.x, chỉ khi có giao thức kiểm định); không sinh bản thảo.

## Tiêu chí nghiệm thu

- Bộ kiểm thử pytest mở rộng phủ F1-F8; dữ liệu 7.1.1 nhập vào 7.2 không mất trường.
- Benchmark theo VALIDATION_PROTOCOL.md chạy lại trên 7.2 cho thấy không thoái lui
  so với 7.1.1 về các ngưỡng quản trị nội bộ.
