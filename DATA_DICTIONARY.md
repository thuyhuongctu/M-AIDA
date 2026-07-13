# DATA_DICTIONARY: Từ điển dữ liệu (M-AIDA v7.1.1)

Mô tả các trường của bản ghi nghiên cứu trong M-AIDA và các cột của tệp xuất
phân tích `forest_data.csv` (tệp CSV chỉ gồm các bản ghi đã khóa, là đầu vào
cho phân tích tổng hợp ba tầng trong R/metafor). Tên trường lấy đúng theo mô
hình dữ liệu Pydantic trong `backend/models.py` và thứ tự cột xuất trong
`backend/main.py`.

## 1. Các cột của forest_data.csv (bản ghi đã khóa)

| Cột | Kiểu | Mô tả |
|---|---|---|
| `study_id` | chuỗi (UUID) | Mã định danh bản ghi, gán tại thời điểm trích xuất |
| `paper_title` | chuỗi | Tiêu đề bài báo nguồn |
| `authors` | chuỗi | Tác giả bài báo nguồn (author) |
| `year` | số nguyên | Năm xuất bản |
| `country` | chuỗi | Quốc gia hoặc vùng của mẫu nghiên cứu |
| `sample_n` | số nguyên | Cỡ mẫu tổng (n) |
| `sample_start` | số nguyên | Năm bắt đầu của dữ liệu mẫu |
| `sample_end` | số nguyên | Năm kết thúc của dữ liệu mẫu |
| `effect_r` | số thực | Hệ số tương quan Pearson r (đại lượng đích chuẩn tắc) |
| `effect_t` | số thực | Thống kê t gốc, nếu bài chỉ báo cáo t (source_stat) |
| `effect_beta` | số thực | Beta chuẩn hóa gốc, nếu bài chỉ báo cáo beta (source_stat) |
| `effect_df` | số nguyên | Bậc tự do kèm thống kê t |
| `p_value` | số thực | Giá trị p được báo cáo |
| `ci_lower` | số thực | Cận dưới khoảng tin cậy |
| `ci_upper` | số thực | Cận trên khoảng tin cậy |
| `doi_measure` | mã phân loại | Thước đo mức độ quốc tế hóa: FSTS, GEO, EXP, FDI, COMP, OTH |
| `performance_measure` | mã phân loại | Thước đo hiệu quả hoạt động: ACC, MKT, LAB, MIX |
| `icrv_regime` | mã phân loại | Biến điều tiết thể chế ICRV: I, II, III, FR, MX (PI gán thủ công) |
| `dpl_phase` | mã phân loại | Biến điều tiết pha số hóa DPL: PRE, SPN, FOL (PI gán thủ công) |
| `cdai_score` | số thực 0-1 | Chỉ số Digital Adoption Index cấp quốc gia (PI gán thủ công) |
| `extraction_confidence` | số thực 0-1 | Điểm tin cậy ba mức của lần trích xuất (confidence) |
| `pi_notes` | chuỗi | Ghi chú xác minh của người nghiên cứu chính (xem mục 3) |
| `locked_at` | thời điểm UTC | Dấu thời gian khóa bất biến |

## 2. Đối chiếu với các trường phân tích khái niệm

| Trường khái niệm | Hiện thực trong 7.1.1 |
|---|---|
| `study_id` | Cột `study_id` |
| `author`, `year` | Cột `authors`, `year` |
| `r` | Cột `effect_r` (giá trị sau xác minh của PI) |
| `n` | Cột `sample_n` |
| `country` | Cột `country` |
| `moderator` | Ba cột `icrv_regime`, `dpl_phase`, `cdai_score`; PI gán thủ công từ bảng tra ngoài, LLM không mã hóa |
| `source_stat` | Suy ra từ trường thống kê gốc được điền (`effect_t` kèm `effect_df`, `effect_beta`, `p_value`, `ci_lower`/`ci_upper`); nếu bài báo cáo r trực tiếp thì chỉ `effect_r` được điền |
| `conversion_formula` | Công thức tất định trong mã nguồn: t sang r theo Cohen (1988); beta chuẩn hóa sang r theo Peterson và Brown (2005); tuyến chuyển đổi ghi chú trong `pi_notes` theo quy ước |
| `confidence` | Cột `extraction_confidence`; dưới 0,70 thì `requires_verification` bật cờ rà soát bắt buộc |
| `status` | Cặp trường `pi_approved` (đã phê duyệt) và `pi_locked` (đã khóa); chỉ bản ghi `pi_locked=True` được xuất |

## 3. Các trường audit (dấu vết kiểm toán)

| Nội dung audit | Hiện thực trong 7.1.1 |
|---|---|
| Giá trị máy đề xuất | Bản ghi `ExtractedEffect` gốc trước xác minh |
| Giá trị sau xác minh | Trường tương ứng sau khi PI áp `field_overrides` qua `PATCH /api/studies/{id}/verify` |
| Nguồn trang, bảng hoặc đoạn | Ghi trong `pi_notes` theo quy ước ghi chép (ví dụ: "Bảng 3, trang 12") |
| Người xác minh (verifier) | Người nghiên cứu chính; định danh ghi trong `pi_notes` theo quy ước |
| Thời điểm | `extracted_at` (thời điểm trích xuất) và `locked_at` (thời điểm khóa), đều UTC |
| Lý do điều chỉnh | Ghi trong `pi_notes` khi có ghi đè |
| Trạng thái rà soát | `requires_verification`, `pi_approved`, `pi_locked` |

Ghi chú: trong 7.1.1, nguồn trang/bảng, định danh người xác minh và lý do
điều chỉnh được lưu dưới dạng ghi chú có cấu trúc trong `pi_notes` theo quy
ước; việc tách chúng thành trường riêng có kiểm tra bắt buộc thuộc lộ trình
phiên bản 7.2.
