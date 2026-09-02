# Rà soát mã nguồn M-AIDA v7.1.1

Ngày 31/08/2026. Phạm vi: toàn bộ `backend/`, `analysis/`, `validation/`,
`frontend/src/`, `scripts/`, cùng các tệp tài liệu ở gốc kho.

Nền: 88 test hiện có **đều đạt** (1 bỏ qua). Mọi phát hiện dưới đây đều nằm
ngoài vùng phủ của bộ test đó, và mỗi phát hiện đều có ca tái hiện chạy được
trong `verify_findings.py` (kèm theo). Không phát hiện nào là suy đoán.

Điểm đáng ghi nhận trước: ba sửa đổi A1–A3 (λ của Peterson & Brown, `df = n − p − 1`,
tách phương sai bậc không / riêng phần) đã có mặt **nhất quán** ở ba nơi —
`backend/extractor.py`, `analysis/effect_size.R`, và máy tính trong
`index.html`. Cổng bằng chứng E1 (từ chối 422 khi có số mà không có trích dẫn
nguyên văn) hoạt động đúng. `machine_proposal` được giữ nguyên qua các lần PI
sửa. Đó là phần lõi làm tốt.

Vấn đề tập trung ở **đường sau khi trích xuất**: bước PI sửa số, bước khóa, và
bước xuất dữ liệu.

---

## A. Nhóm làm sai số liệu đưa vào mô hình gộp

### A1 · PI sửa `effect_r` nhưng `variance_r` không được tính lại (NGHIÊM TRỌNG)

`main.py:verify_study` gọi `resolve_overridden_r` để tính lại r, nhưng **không**
tính lại `variance_r`, `variance_formula`, `metric_type`, `estimand_source`,
`source_controls`, `df_source`, `lambda_applied`, `r_source`, hay
`extraction_confidence`. Bản ghi được lưu với r mới và phương sai cũ.

Tái hiện: n = 200, r trích xuất = 0.30 → `variance_r` = 0.00416131. PI sửa r
thành 0.80. Phương sai đúng phải là (1 − 0.80²)² / 199 = 0.00065126, nhưng bản
ghi vẫn giữ 0.00416131 — **gấp 6,4 lần**. Trong mô hình MARA ba cấp, trọng số
là nghịch đảo phương sai, nên nghiên cứu này bị đánh trọng số thấp hơn mức
đúng khoảng 6 lần.

Đây là lỗi có hướng: PI thường sửa r lên hoặc xuống theo bản gốc, và sai số
trọng số không triệt tiêu ngẫu nhiên.

### A2 · PI chuyển sang t/df thì đại lượng đổi bản chất nhưng nhãn không đổi (NGHIÊM TRỌNG)

Cùng gốc lỗi. Bản ghi trích xuất được r = 0.30 (bậc không). PI sửa sang
`effect_t = 2.5`, `effect_df = 187`, `n_predictors = 12`. r được tính lại thành
0.1798 — một **tương quan riêng phần**. Nhưng bản ghi vẫn ghi:

```
metric_type      = zero_order      (phải là partial)
source_controls  = False           (phải là True)
variance_formula = (1 - r^2)^2 / (n - 1)   (phải là (1 - r^2)^2 / df)
```

Đúng điều mà A3 trong bản sửa công thức đặt ra để ngăn — gộp chung tương quan
riêng phần với tương quan bậc không — vẫn xảy ra, chỉ là qua đường PI sửa thay
vì qua đường trích xuất.

### A3 · Beta ngoài khoảng làm bản ghi mất hẳn cỡ ảnh hưởng mà vẫn khóa được (NGHIÊM TRỌNG)

`resolve_overridden_r` trả `None` khi `|β| > 0.5`. `verify_study` gán thẳng
`data["effect_r"] = None` mà không kiểm tra, và **không** bật lại
`beta_outside_pb_domain`.

Tái hiện: bản ghi β = 0.30 (r = 0.344). PI sửa β thành 0.70. Kết quả:

```
effect_r = None    beta_outside_pb_domain = False    requires_verification = False
POST /lock -> 200, pi_locked = True
```

Một bản ghi không có cỡ ảnh hưởng nào được đóng dấu là dữ liệu cuối cùng. Nó sẽ
lọt vào CSV xuất ra với ô `effect_r` rỗng.

### A4 · CSV xuất ra bỏ toàn bộ cột phương sai và xuất xứ (NGHIÊM TRỌNG)

`export_csv` cố định 23 tên cột và dùng `extrasaction="ignore"`. 14 trường mà
bản sửa A1–A3 tạo ra **không có trong tệp xuất**:

`variance_r`, `variance_formula`, `metric_type`, `estimand_source`,
`source_controls`, `df_source`, `lambda_applied`, `r_source`, `n_source`,
`n_predictors`, `evidence_quote`, `evidence_page`, `requires_verification`,
`beta_outside_pb_domain`.

Hệ quả trực tiếp: tệp bàn giao sang Stata **không mang phương sai**, nên trọng
số phải tính lại ở phía Stata bằng công thức bậc không cho mọi bản ghi — đúng
cái mà A3 nói là sai. Và vì `metric_type` không được xuất, không có cách nào mã
hóa nó làm biến điều tiết như ghi chú trong `from_t` yêu cầu.

`DATA_DICTIONARY.md` mô tả các trường này như một phần của bộ dữ liệu; tệp xuất
thực tế không có chúng.

---

## B. Nhóm phá cơ chế quản trị "khóa bất biến"

### B1 · Đặt `pi_locked` qua `/verify`, đi vòng qua cổng kiểm chứng (NGHIÊM TRỌNG)

`verify_study` chỉ chặn một trường (`machine_proposal`); mọi trường khác của
model đều ghi đè được. Bao gồm chính `pi_locked` và `locked_at`.

Tái hiện: bản ghi suy từ β, `requires_verification = True`. Gọi thẳng
`POST /lock` bị chặn đúng (422). Nhưng:

```
PATCH /verify  field_overrides = {"pi_locked": true, "locked_at": "2020-01-01T00:00:00"}
-> pi_locked = True, locked_at = 2020-01-01, requires_verification = True
PATCH /verify lần sau -> 409
```

Bản ghi **chưa** được kiểm chứng nay đã khóa, mang dấu thời gian lùi về năm
2020, và không sửa lại được nữa vì mọi lần `/verify` sau đều 409. Cơ chế "khóa
bất biến kèm dấu thời gian, không ai sửa lén được" trong kịch bản thuyết minh
không đứng vững trước chính API của nó.

### B2 · Ghi đè `study_id` sinh ra bản ghi trùng (NGHIÊM TRỌNG)

`_studies.put()` khóa theo `study_id`. Ghi đè trường này tạo hàng mới thay vì
sửa hàng cũ:

```
trước: 1 bản ghi     sau: 2 bản ghi (bản gốc vẫn còn nguyên)
```

Trong bộ dữ liệu meta-analysis, đây là đếm trùng hiệu ứng — vi phạm giả định
độc lập mà chính mô hình ba cấp được dựng để xử lý.

### B3 · Ghi đè được `extraction_confidence` và `evidence_quote` (TRUNG BÌNH)

```
field_overrides = {"extraction_confidence": 0.99, "evidence_quote": "rewritten"}
-> confidence = 0.99, evidence_quote = "rewritten"
```

Điểm tin cậy là đại lượng do máy sinh, không phải ý kiến của PI; trích dẫn
nguyên văn là hiện vật của cổng E1. Cho phép sửa hai trường này làm hỏng dấu
vết kiểm toán. Việc `machine_proposal` được giữ lại có giảm nhẹ hậu quả, nhưng
cách đúng là **danh sách trắng** các trường PI được sửa, thay vì danh sách đen
một phần tử.

---

## C. Nhóm bền vững và trùng lặp

### C1 · JSON của LLM không được kiểm kiểu, trả về 500 (TRUNG BÌNH)

Mô hình trả `"effect_r": "0.35"` (chuỗi thay vì số) làm `clamp_r` ném
`TypeError`, nổi lên thành HTTP 500 với thông điệp
`'<' not supported between instances of 'str' and 'float'`.

Cùng chỗ này, khi `json.loads` thất bại, `_call_llm` trả `{}` và **im lặng** —
bản ghi được tạo với mọi trường rỗng và `confidence = 0`, thay vì báo lỗi. Đầu
ra của LLM là dữ liệu không tin cậy; nó cần một lớp kiểm lược đồ trước khi vào
`_build_effect`.

### C2 · `lambda_applied = True` cả khi số hạng λ không được áp dụng (TRUNG BÌNH)

Với β = −0.30, λ = 0 và r = −0.294 (không cộng 0.05). Nhưng cả
`backend/extractor.py:390` lẫn `analysis/effect_size.py:248` đều ghi cứng
`lambda_applied = True`. `models.py:197` định nghĩa trường này là "True khi số
hạng +0.05·λ đã được áp dụng". Bản ghi khai sai điều nó vừa làm. Sửa:
`lambda_applied = (lam == 1.0)`.

### C3 · `analysis/effect_size.py` là bản cài đặt thứ hai, không ai gọi (TRUNG BÌNH)

Module này khai `__version__ = "8.0.0"` và cài đặt lại toàn bộ phép quy đổi,
nhưng **không tệp nào ngoài test của chính nó import nó**. Hai bản cài đặt song
song đã lệch nhau ở hành vi:

| Tình huống | `backend/extractor.py` | `analysis/effect_size.py` |
|---|---|---|
| \|β\| > 0.5 | trả `None`, bản ghi gắn cờ | ném `ConversionError` |
| thiếu `n_predictors` và `df` | vẫn tạo bản ghi, `df_source=None` | ném `ConversionError` |
| phương sai Fisher z | không tính | tính `var_z` |

`var_z` chỉ tồn tại ở module không được gọi, nghĩa là **phương sai trên thang z
— đại lượng mô hình ba cấp thực sự cần — không bao giờ được sinh ra trong
đường chạy thật**. Cần chọn một nguồn duy nhất: hoặc backend import module
này, hoặc gỡ nó đi.

---

## D. Vệ sinh kho và hồ sơ

- **129 tệp `.bak` được commit** (`README.md.bak`, `CHANGELOG.md.bak`,
  `backend/tests/*.py.bak`, …). Với một kho là hiện vật nộp kèm hồ sơ bản quyền
  và có DOI Zenodo, các tệp sao lưu trung gian làm mờ ranh giới tác phẩm được
  đăng ký. Nên xóa và thêm `*.bak` vào `.gitignore`.
- **Số hiệu phiên bản không khớp nội dung.** `CITATION.cff`, `README.md` và
  `main.py` đều ghi 7.1.1, trong khi `CHANGELOG.md` xếp ba sửa đổi A1–A3 vào
  mục "Chưa phát hành". Mã đang chạy **đã có** các sửa đổi đó. Với bản nộp có
  DOI, phiên bản mang các sửa đổi công thức hiện không có số hiệu riêng.
- **Cắt văn bản PDF ở 40.000 ký tự** (`extractor.py:301`) không được ghi trong
  tài liệu. Với bài dài, bảng kết quả có thể nằm ngoài đoạn được gửi cho mô
  hình; khi đó bản ghi trống là do cắt chứ không phải do bài không có số liệu.
- **Giao diện thiếu 18 trường của backend.** `frontend/src/types.ts` không khai
  `metric_type`, `variance_r`, `evidence_quote`, `evidence_page`,
  `lambda_applied`, `df_source`, `estimand_source`, `n_predictors`… PI không
  nhìn thấy các trường này trên màn hình kiểm chứng, nên câu "tôi tự kiểm từng
  trường so với trang nguồn" trong kịch bản thuyết minh chỉ đúng với phần
  trường mà giao diện có hiển thị.
- `datetime.utcnow()` (5 chỗ) đã bị khuyến cáo bỏ; nên dùng
  `datetime.now(timezone.utc)`.

---

## Thứ tự đề nghị xử lý

1. **A4 và A1/A2** trước hết: nếu bộ dữ liệu P6 hiện tại được xuất qua
   `/export/csv` thì nó đang thiếu phương sai và nhãn đại lượng, và mọi bản ghi
   từng bị PI sửa đều mang phương sai cũ. Cần xác định bộ dữ liệu đang dùng
   được sinh ra bằng đường nào trước khi chạy lại mô hình gộp.
2. **B1 và B2**: đổi `field_overrides` sang danh sách trắng. Đây là sửa nhỏ về
   mã nhưng là điểm mấu chốt của tuyên bố toàn vẹn dữ liệu.
3. **A3, C1, C2**: kiểm tra giá trị trả về và kiểu dữ liệu.
4. **C3**: chọn một nguồn công thức duy nhất; nếu giữ `analysis/effect_size.py`
   thì nối `var_z` vào đường xuất dữ liệu.
5. **D**: dọn `.bak`, thống nhất số phiên bản trước lần nộp hồ sơ kế tiếp.

Hai điểm cần cô quyết trước khi em viết bản vá:

- Khi PI sửa số, `extraction_confidence` nên **giữ nguyên** (điểm của máy, sửa
  của người ghi riêng) hay **đặt lại thành 1.0** (đã có người xác nhận)?
- Danh sách trắng trường PI được sửa nên gồm những gì? Đề xuất tối thiểu:
  `effect_r`, `effect_t`, `effect_df`, `effect_beta`, `n_predictors`,
  `sample_n`, `sample_start`, `sample_end`, `p_value`, `ci_lower`, `ci_upper`,
  `doi_measure`, `performance_measure`, `icrv_regime`, `dpl_phase`,
  `cdai_score`, `country`, `year`, `paper_title`, `authors`.

---

*Ca tái hiện: `verify_findings.py` ở gốc kho. Chạy `python3 verify_findings.py`
sau khi cài `backend/requirements.txt`.*
