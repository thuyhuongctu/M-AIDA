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

### 1b. Các cột bổ sung trong tệp xuất từ 7.2.0

Từ 7.2.0 tệp xuất mang **mọi** trường của bản ghi (thứ tự theo model backend), không chỉ 23 cột trên.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `n_predictors` | số nguyên | Số biến giải thích của mô hình nguồn (p), dùng cho df = n − p − 1 |
| `metric_type` | `zero_order` / `partial` | Đại lượng ước lượng: tương quan bậc không hay riêng phần |
| `estimand_source` | `observed` / `imputed_pb2005` | Nguồn gốc: quan sát trực tiếp (r, t) hay suy từ β theo Peterson & Brown |
| `source_controls` | lôgic | Thống kê nguồn có kiểm soát biến khác không |
| `df_source` | `reported` / `derived` | df báo cáo hay suy từ n − p − 1 |
| `lambda_applied` | lôgic | True chỉ khi số hạng +0,05·λ đã được cộng (β ≥ 0) |
| `beta_outside_pb_domain` | lôgic | True khi \|β\| > 0,5: không có r, không được khóa |
| `variance_r` | số thực | Phương sai thang r: (1 − r²)²/(n − 1) bậc không; (1 − r²)²/df riêng phần |
| `variance_formula` | chuỗi | Công thức phương sai đã dùng |
| `variance_z` | số thực | Phương sai thang Fisher z: 1/(n − 3) bậc không; 1/(df − 1) riêng phần |
| `r_source`, `n_source` | chuỗi | Xuất xứ của r (reported/derived/imputed) và n |
| `evidence_page`, `evidence_quote`, `n_evidence_page`, `n_evidence_quote` | số / chuỗi | Trích dẫn nguyên văn của cổng E1 (bất biến sau trích xuất) |
| `text_truncated` | lôgic | True khi văn bản PDF vượt 40.000 ký tự và bị cắt trước khi gửi mô hình |
| `requires_verification`, `df_imputed` | lôgic | Cờ rà soát |
| `pi_edited_fields` | JSON (danh sách) | Tên các trường PI đã sửa qua `/verify` |
| `pi_override_at` | thời điểm UTC | Lần sửa gần nhất của PI |
| `machine_proposal` | JSON | Ảnh chụp đề xuất của máy trước mọi sửa đổi (bất biến) |
| `derived_from`, `notion_page_id` | chuỗi | Liên kết thế hệ khóa trước; trang Notion |

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
