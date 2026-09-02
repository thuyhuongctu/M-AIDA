# Changelog: M-AIDA (Meta-Analysis Intelligent Data Assistant)

All notable changes to this project are documented here. Versions follow the
internal release line used during the doctoral meta-analysis (P6).

## [7.2.1] - 2026-09-03: một số hiệu phiên bản duy nhất; giao diện hiển thị trường dẫn xuất

Bản vá nhỏ sau 7.2.0, không đổi công thức, không đổi lược đồ dữ liệu, không
đụng bản ghi đã khóa.

- Số hiệu: `/api/health` của 7.2.0 vẫn trả `"version": "7.1.1"` trong khi
  tài liệu OpenAPI ghi 7.2.0. Nay backend có một hằng `APP_VERSION` duy nhất
  (tiêu đề ứng dụng, OpenAPI, `/api/health` đều đọc từ đó); giao diện lấy số
  hiệu từ `/api/health` thay vì ghi cứng; test
  `test_721_version_consistency.py` khóa `APP_VERSION` = `backend/pyproject.toml`
  = `CITATION.cff` = `.zenodo.json`.
- Giao diện xác minh (`VerificationPanel`): thêm ô sửa `n_predictors` (cần cho
  t/β từ hồi quy, df = n − p − 1); hiển thị chỉ đọc các trường máy chủ dẫn xuất
  (`metric_type`, `estimand_source`, `r_source`, `df_source`, `variance_r`,
  `variance_formula`, `variance_z`, `source_controls`, `lambda_applied`,
  `beta_outside_pb_domain`), khối "Machine proposal" bất biến
  (`extraction_confidence`, trích dẫn bằng chứng và trang, cảnh báo
  `text_truncated`), và dòng `pi_edited_fields` / `pi_override_at`. Cảnh báo
  rõ khi bản ghi không có r nên không khóa được. Chỉ gửi các trường trong
  danh sách trắng `PI_EDITABLE_FIELDS` làm `field_overrides`.
- Trình khách API: thông điệp lỗi hiển thị trường `detail` của FastAPI
  (ví dụ lý do 422 của danh sách trắng hay cổng khóa) thay vì
  "Request failed with status code 422".
- Kiểm thử: 76 test backend, 20 test `analysis/` đạt; `tsc --noEmit` và
  `vite build` sạch.
- Bản ghi cũ (trước 7.2.0) không có phương sai: `/verify` nay tự dẫn xuất
  `variance_r`, `variance_z`, `metric_type`… từ thống kê sơ cấp ngay lần xác
  minh đầu (không cần sửa trường nào), nên bản ghi nhập từ CSV hay từ kho SQLite
  cũ khoá được thay vì kẹt 422 vĩnh viễn. Ứng dụng bảo vệ (`demo/run_defense.py`)
  gieo bản ghi qua cùng hàm dẫn xuất, nên 18 bản ghi mẫu đều có phương sai và
  người trình bày xác minh + khoá được bản ghi chờ; `demo/smoke_test.py` kiểm
  đúng đường này.
- Trang web (GitHub Pages): số hiệu và DOI phiên bản lấy từ 7.2.0
  (`assets/data/site-metrics.json` là nguồn duy nhất: `version`, `version_doi`,
  và `generation` = thế hệ khoá dữ liệu v7.1.1 tách riêng); ghi chú "tạm thời"
  nói rõ 7.2.0 là bản phần mềm, không khoá lại kho dữ liệu; các trang
  commercial, defense, huong, asia, asia-maida-paper, styleguide cập nhật theo;
  `scripts/check_site_metrics.py` đạt trên 24 trang.
- DOI: ghi DOI phiên bản Zenodo của v7.2.0 (`10.5281/zenodo.22259090`) vào
  CITATION.cff và README. **DOI phiên bản của chính bản 7.2.1 là
  `10.5281/zenodo.22260059`** (tag `v7.2.1` = `d2ea8e3`), ghi bổ sung sau khi
  phát hành. Ba bản ghi Zenodo ngày 03/09/2026 là bản thay thế, KHÔNG trích dẫn:
  `22258783` và `22258977` (nhãn `v.7.2.0`, lưu commit `3c8de32` chưa vá) và
  `22259684` (nhãn `v7.2.1`, lưu commit `3ff42c4` tức mã 7.2.0). Tác giả đã yêu
  cầu Zenodo gỡ ba bản ghi này.
- DOI khái niệm: M-AIDA có **hai chuỗi Zenodo song song**. Chuỗi lưu tự động từ
  GitHub có DOI khái niệm `10.5281/zenodo.21850575` (luôn trỏ tới bản phát hành
  mới nhất); bản nộp tay ngày 09/07/2026 là một chuỗi riêng
  (`10.5281/zenodo.21282516`, phiên bản `.21282517`) và mãi trỏ tới v7.1.1.
  CITATION.cff, README và trang web trước đây ghi `21282516` là "DOI mọi phiên
  bản" — không đúng với chuỗi đang chạy. Nay: DOI khái niệm = `21850575`; bản
  nộp tay giữ nguyên, ghi rõ là bản lưu trữ v7.1.1 mà luận án và hồ sơ đăng ký
  bản quyền trích dẫn. Hai bản ghi Zenodo gắn nhãn `v.7.2.0`
  (22258783, 22258977) sinh ra từ release gắn sai tag (trỏ `3c8de32` chưa vá)
  là bản thay thế, không trích dẫn.

## [7.2.0] - 2026-09-03: đường sau trích xuất (PI sửa, khóa, xuất) và số hiệu cho A1–A3

Phát hành gộp ba mục "Chưa phát hành" bên dưới (A1–A3, E1, demo) cùng bản vá
cho mười phát hiện của `CODE_REVIEW_2026-08-31.md` (ca tái hiện:
`verify_findings.py`). Không đụng vào bản ghi P6 đã khóa. Bộ dữ liệu P6 của
luận án không bị ảnh hưởng bởi các lỗi này (bảng 17 cột do tác giả quản lý,
phương sai tính trong R từ n bằng `escalc(ZCOR)`), nhưng mọi tuyên bố về công
cụ từ nay dẫn 7.2.0.

- A1/A2/A3 (PI sửa số): mọi sửa trên `effect_r`, `effect_t`, `effect_df`,
  `effect_beta`, `n_predictors`, `sample_n` đi qua đúng hàm dẫn xuất của đường
  trích xuất (`StatisticalExtractor.derive_from_primary`), nên `variance_r`,
  `variance_z`, `variance_formula`, `metric_type`, `estimand_source`,
  `source_controls`, `df_source`, `lambda_applied`, `r_source`,
  `beta_outside_pb_domain` được tính lại cùng lúc. Bản ghi mất r (β ngoài
  khoảng) tự bật `requires_verification` và `POST /lock` từ chối (422).
- A4 (xuất CSV): `/api/studies/export/csv` xuất **mọi** trường của bản ghi
  theo thứ tự model (kể cả `variance_r`, `variance_z`, `metric_type`,
  `evidence_quote`, `machine_proposal` dạng JSON).
- B1/B2/B3 (khóa bất biến): `field_overrides` chuyển sang **danh sách trắng**
  `PI_EDITABLE_FIELDS` (20 trường: sáu thống kê sơ cấp, mã điều tiết, siêu dữ
  liệu). `pi_locked`, `locked_at`, `study_id`, `machine_proposal`,
  `extraction_confidence`, `evidence_*` và mọi trường dẫn xuất bị từ chối 422
  thay vì bị bỏ qua hay áp lặng lẽ. Sửa của người ghi ở `pi_edited_fields`
  (danh sách tên trường) và `pi_override_at`; `extraction_confidence` là điểm
  của máy, không bao giờ bị ghi đè.
- C1 (đầu ra LLM): kiểm kiểu; chuỗi số được ép kiểu, giá trị không phải số
  và JSON hỏng trả 422 (`MalformedLLMOutputError`), không còn 500 và không còn
  bản ghi rỗng.
- C2: `lambda_applied = (β ≥ 0)` ở cả backend lẫn `analysis/effect_size.py`.
- C3: `variance_z` (1/(n − 3) bậc không; 1/(df − 1) riêng phần) nay được
  sinh trong đường chạy thật; test `test_C3_backend_agrees_with_analysis_module`
  khóa hai cài đặt khớp nhau trên r, `variance_r`, `variance_z`, `lambda_applied`.
- D: xóa 129 tệp `.bak` khỏi kho và thêm `*.bak` vào `.gitignore`; giới hạn
  40.000 ký tự văn bản PDF ghi thành hằng `PDF_TEXT_LIMIT` và trường
  `text_truncated` trên bản ghi; `datetime.utcnow()` → `datetime.now(timezone.utc)`;
  `frontend/src/types.ts` khai đủ trường của backend (giao diện hiển thị các
  trường mới là việc của 7.2.1).
- Kiểm thử: `backend/tests/test_720_post_extraction.py` (11 test, mỗi test ghim
  một phát hiện); toàn bộ 74 test backend và 20 test `analysis/` đạt.

## Chưa phát hành: sửa ba công thức A1–A3 theo bản rà soát Paper 6 (04/08/2026)

Bước 1 trong bảy bước chạy lại. Ba lỗi tầng công thức được sửa đồng bộ ở
backend Python, máy tính demo trong trình duyệt, phần mô tả phương pháp
trên trang, và module R mới `analysis/effect_sizes.R` (kèm testthat).
LƯU Ý: các bản ghi P6 đã khóa suy từ beta hoặc từ t thiếu df PHẢI được mã
lại (bước 2) trước khi chạy lại mô hình gộp.

- A1, Peterson & Brown (2005) đầy đủ: `r = 0.98·β + 0.05·λ`, λ = 1 khi
  β ≥ 0. Bản cũ bỏ số hạng λ nên mọi hiệu ứng dương suy từ β bị hạ thấp
  đúng 0,05. Ngoài khoảng |β| ≤ 0,5 nay KHÔNG quy đổi (trả về None/NA và
  loại khỏi gộp) thay vì chặn về ±1.
- A2, Bậc tự do cho t từ hồi quy bội: `df = n − p − 1` với trường mới
  `n_predictors`; không còn mặc định `n − 2`. Thiếu số biến giải thích thì
  bản ghi không quy đổi và gắn cờ chờ PI, kèm `df_source` (reported/derived).
- A3: Tách loại thước đo bằng trường `metric_type` (zero_order / partial /
  semipartial) và tính phương sai đúng theo loại:
  bậc không `(1−r²)²/(n−1)`, riêng phần `(1−r²)²/df`; lưu `variance_r` và
  `variance_formula` trên từng bản ghi để kiểm toán.
- Kiểm thử: viết lại `test_effect_size_conversions.py` với ví dụ tính tay
  cho cả ba công thức; cập nhật `test_712_governance.py` theo hành vi mới
  (58 test đạt). Test R: `analysis/test_effect_sizes.R`.
- Gói chuẩn độc lập `analysis/effect_size.py` (v8.0.0): thêm Fisher z +
  var_z (A4), `legacy_r` đo chênh lệch với cách tính cũ, và `recode_csv`
  mã lại CSV kèm cột `r_legacy`/`delta_r`; 19 kiểm thử tính tay
  (`analysis/test_effect_size.py`, chạy được không cần pytest); bộ mẫu
  `mau_cu.csv` → `mau_moi.csv` làm kiểm thử hồi quy (khớp từng byte,
  chứng minh mã ổn định; tính đúng đắn nằm ở 19 test tính tay). Backend
  đồng bộ theo ngữ nghĩa gói: bản ghi suy từ β mang `metric_type =
  partial` (β đã kiểm soát các biến khác), df suy được cả cho đường β khi
  có `n_predictors`.
- Bản R chuẩn `analysis/effect_size.R` (thay `effect_sizes.R` +
  `test_effect_sizes.R` tạm thời): tự kiểm tra khi chạy
  `Rscript analysis/effect_size.R`, kèm khung quy trình metafor bước 3–7
  (ba cấp/hai cấp, phương sai vững theo cụm, khoảng dự báo, PET-PEESE,
  giả thuyết chữ S).
- QUYẾT ĐỊNH CHỐT (04/08/2026): bản ghi suy từ β mang `metric_type =
  zero_order`: P&B hiệu chuẩn công thức để khôi phục r bậc không; nguồn
  gốc tách sang hai trường mới `estimand_source` (observed /
  imputed_pb2005) và `source_controls`. Ba lớp: r báo cáo (zero_order ·
  observed), t hồi quy (partial · observed), β quy đổi (zero_order ·
  imputed: chỉ phân tích độ nhạy, không vào mô hình chính vì phương sai
  bậc không bỏ qua sai số quy đổi). Đồng bộ Python + R + backend +
  migrate_v8; test đảo lại tương ứng (20 test tay + 60 test backend).
- CHÍNH SÁCH THẾ HỆ KHÓA: tập khóa v7.1.1 (đã có DOI) giữ nguyên, không
  ghi đè; việc mã lại theo công thức mới sinh tập v8.0.0 như một lần khóa
  độc lập, mỗi bản ghi mang trường mới `derived_from` trỏ về bản gốc,
  phát hành DOI phiên bản mới và ghi nhật ký sai lệch OSF. Trang công
  khai hạ `r̄ = .074` xuống trạng thái tạm thời (thuộc v7.1.1, chờ thế hệ
  khóa v8.0.0) ở ô KPI, đoạn phương pháp và chú thích biểu đồ rừng.

## Chưa phát hành: E1, không bao giờ bịa kết quả trích xuất (04/08/2026)

Sổ đăng ký vấn đề E1: đường tải PDF trả về cùng một kết quả cho mọi tệp,
mâu thuẫn với chính tuyên bố "không có khóa thì nói thẳng, không bịa".

- Demo trong trình duyệt (index.html + docs/index.html): PDF thả vào bị
  TỪ CHỐI tường minh kèm lời giải thích, không nạp mẫu ngầm nữa; thay
  bằng ba bài mẫu bấm chọn minh họa đúng ba đường chuyển đổi (r trực
  tiếp / t → r suy df = n − p − 1 / β chỉ độ nhạy); CSV thêm cột
  n_predictors; toàn bộ nhãn nói rõ "bản ghi đã trích sẵn (minh họa)".
- Backend: GỠ BỎ hoàn toàn đường fallback diễn tập (demo_fallback.py và
  nhánh trả fallback trong /api/extract): trích xuất lỗi thì lỗi hiện
  lên thành trạng thái, demo mode hay không; /api/health chỉ còn hai chế
  độ live / unavailable.
- Cổng dẫn chứng: hai trường mới `evidence_page` + `evidence_quote`
  (câu nguyên văn chứa thống kê tiêu điểm) bắt buộc trong prompt và lược
  đồ; thống kê không kèm dẫn chứng bị TỪ CHỐI 422, không tạo bản ghi
  (EvidenceMissingError).
- Kiểm thử hồi quy E1: hai PDF khác nhau phải cho hai bản ghi khác nhau;
  không khóa thì 503 ở mọi chế độ; thiếu dẫn chứng thì 422 và store
  trống. 62 test đạt.

Rà soát E2 kèm theo (kho 236 có nhiễm bản ghi mặc định không?): 0 khớp
với bản ghi diễn tập; 12 cụm trùng (r, n) khác study, 22/26 thành viên
là is_estimated=1 thuộc dải S190+ với n tròn, trùng đúng nhóm 47 bản ghi
phải thu hồi thống kê nguồn. Báo cáo và bảng đối chiếu ngược nằm ở
p6/data/v8/ (kho luận án).

## Chưa phát hành: bộ trình diễn `demo/` (15/07/2026)

Đóng gói trình diễn, KHÔNG thay đổi mã lõi 7.1.x: `demo/run_defense.py`
khởi động đúng backend FastAPI hiện có, nạp sẵn bản ghi thật từ cơ sở dữ
liệu P6 đã khóa (18 dòng mẫu trong `demo/demo_seed.csv`, hoặc toàn bộ qua
`MAIDA_SEED_CSV`), và phục vụ giao diện một tệp `demo/ui.html` chạy bằng
Python thuần. Hướng dẫn tiếng Việt: `demo/HUONG_DAN_BAO_VE.md`.

## 7.1.2 (15/07/2026)

Bản vá quản trị: đưa mã về đúng với giao thức đã mô tả trong tài liệu,
không thay đổi kết quả của các bản ghi P6 đã khóa.

- Chặn phòng vệ r trong [-1, 1] cho mọi tuyến chuyển đổi (t bị chặn sẵn
  theo công thức; beta và ghi đè r trực tiếp nay được chặn tường minh).
- Gắn cờ bắt buộc kiểm chứng khi |beta| > 0,5, ngoài miền dẫn xuất của
  Peterson & Brown (2005).
- Thực thi quy tắc df = n - 2 khi df không được báo cáo, kèm cờ
  `df_imputed` minh bạch.
- Lưu `machine_proposal`: ảnh chụp bất biến các giá trị máy đề xuất tại
  thời điểm trích xuất, không thể ghi đè, tách bạch máy đề xuất với
  con người quyết định ở cấp từng bản ghi.
- 10 unit test mới, gồm test API xác nhận bản ghi đã khóa trả 409.

## [Unreleased]
- Web: unified public web app (overview, method, positioning, forest plot,
  interactive study atlas, in-browser demo tool) served via GitHub Pages at
  https://thuyhuongctu.github.io/M-AIDA/ from the repository root.
  (Corrected 2026-08-13: this line previously said "and `docs/`". The Pages
  workflow stages `_site` from root `*.html` plus `assets/`, `icons/` and
  `voice/`; it never reads `docs/`. The stale claim is the likely reason a
  superseded copy of the site sat under `docs/` for months without anyone
  correcting it. Those two dead pages were removed on the same date.)

## [7.1.1] - 2026-07-09
- Documentation: revised public-facing wording to describe the extraction layer
  as a configurable LLM-provider adapter rather than a contribution from any
  external model/vendor.
- Configuration: added provider-neutral `LLM_PROVIDER`, `LLM_API_KEY`, and
  `LLM_MODEL` environment variables while retaining backward-compatible aliases
  for existing local deployments.
- Repository hygiene: removed the legacy standalone webapp artifact that used a
  direct model-specific API call and model-specific audit wording. The maintained
  application remains under `backend/` and `frontend/`.

## [7.1.0] - 2026-07-09
- Packaging: added `backend/pyproject.toml` (PEP 621) making the backend
  pip-installable (`pip install -e backend[test]`), with pinned runtime
  dependencies and a `test` extra.
- Tests: added `backend/tests/` (pytest) pinning the Cohen (1988) t→r and
  Peterson & Brown (2005) β→r conversions, sign preservation, the unit-interval
  bound, and the three-level confidence scheme / PI-review threshold.
- Frontend: migrated from the deprecated Create-React-App (`react-scripts` 5,
  which cannot build under React 19) to **Vite 6** + `@vitejs/plugin-react`.
  Added `vite.config.ts`, root `index.html`, `tsconfig.json`, `src/vite-env.d.ts`,
  and `frontend/.env.example`; the API base URL now reads `import.meta.env.VITE_API_URL`.
  Build output stays in `build/` so the Docker/nginx setup is unchanged.
- CI: added `.github/workflows/ci.yml` running the backend pytest suite
  and the frontend Vite production build on every change.

## [7.0.1] - 2026-06-10
- Schema alignment with the P6 analysis database: `cdai_score` relabelled to
  country Digital Adoption Index (0-1); ICRV enum corrected to the
  institutional I/II/III/FR/MX taxonomy; DOI-type and performance-type enums
  aligned to the coded study database.
- ICRV regime, DPL phase, and cDAI moved to PI-assigned fields (the LLM no
  longer codes them); extraction limited to statistical quantities.
- Model ID made configurable through the project settings layer.

## [7.0.0] - 2026-06-08
- Two-tab workflow finalised: **Extract** (LLM PDF to effect sizes) and
  **Verify & Lock** (PI dashboard, overrides, immutable lock).
- Pydantic v2 domain models: `ExtractedEffect`, `StudyDatabaseEntry`,
  `VerificationDecision`.
- Notion two-way sync (`notion_sync.py`) for the coded study database.
- CSV export restricted to `pi_locked=True` records to `forest_data.csv`,
  the analysis input for the three-level meta-analysis (k=238, K=288).
- Dockerised (backend FastAPI :8765, frontend React :3000).

## Earlier (internal, pre-release)
- v6.x: extraction-hierarchy conversion (t/F/β to Pearson r) hardening.
- v5.x: verification dashboard and override/adjudication logic.
- v1-v4: prototype PDF text extraction (PyMuPDF) and LLM prompt iterations.

> Version history reflects iterative, human-directed development; see the git
> commit log for the full, dated trail.

## Governance note - 2026-07-13

- **[7.1.1] is declared the Registered Reference Release (frozen).** This is
  the version deposited in the copyright-registration dossier filed through
  Can Tho University and the version used in the dissertation (P6). No direct
  changes may be made to the 7.1.1 source, architecture, features, or UI; see
  `IP_REGISTER.md` for the full post-freeze rules and the 7.1.0/7.1.1
  reconciliation note.
- **Semantic Versioning rules from this point on:**
  - `7.1.2+` (patch): bug fixes only; no new features, no architecture change.
  - `7.2.0` (minor): new features that keep the current architecture and
    purpose ("Meta-Analysis Intelligent Data Assistant"); developed on a
    separate branch, never on the 7.1.1 release.
  - `8.0.0` (major): substantial changes to architecture or scope.
- Supplementary IP registration for any later version is considered only when
  that version contains significant creative changes, and only after
  consulting an intellectual-property specialist.
