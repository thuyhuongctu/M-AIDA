# Changelog: M-AIDA (Meta-Analysis Intelligent Data Assistant)

All notable changes to this project are documented here. Versions follow the
internal release line used during the doctoral meta-analysis (P6).

## 8.0.0 (chưa phát hành, 02/10/2026): dịch vụ web nhiều người dùng (beta kín)

Lõi khoa học (trích xuất có cổng bằng chứng, dẫn xuất phương sai, duyệt và khóa,
xuất CSV đủ trường) giữ nguyên 7.2.3; không đổi công thức hay bản ghi đã khóa.
Bản này bọc lõi đó để nhiều nhà nghiên cứu dùng chung một máy chủ.

- **Danh tính** (`backend/auth.py`): `MAIDA_AUTH_MODE` = `admin_key` (mặc định,
  đúng hành vi 7.2: một người vận hành, khóa dùng chung trên yêu cầu ghi),
  `supabase` (JWT của Supabase Auth xác minh cục bộ bằng JWKS ES256/RS256 hoặc
  secret HS256; kiểm tra `aud`, `exp`) hoặc `mock` (token ký cục bộ, chỉ để kiểm
  thử). Ở hai chế độ sau mọi tuyến `/api/*` trừ `/api/health`, `/api/config`
  đều cần `Authorization: Bearer`. Tài khoản mới tự tạo khi đăng nhập lần đầu,
  được cấp `MAIDA_BETA_CREDITS` (10) tín dụng; e-mail trong `MAIDA_ADMIN_EMAILS`
  có vai trò admin.
- **Dữ liệu** (`backend/db.py`, `backend/store.py`, Alembic `backend/alembic/`):
  SQLAlchemy 2 thay `sqlite3` thuần; cùng lược đồ chạy trên SQLite (cục bộ,
  demo, test) và Postgres (`DATABASE_URL`, Supabase). Bảng mới `users`,
  `extraction_jobs`, `llm_calls`, `credit_ledger`, `orders` (để sẵn), `audit_log`;
  bảng `studies` thêm `owner_id`, `workspace_id` và các cột lọc; tệp SQLite của
  7.x được di trú tại chỗ (mọi bản ghi cũ thuộc chủ `local`). `StudyStore` giữ
  nguyên giao diện `get/put/values/clear` nên `demo/run_defense.py` và test cũ
  không đổi; thêm tham số `owner_id`: người này không đọc, sửa, khóa, xóa hay
  xuất bản ghi của người kia (trả 404, không phải 403, để không dò được id).
- **Job trích xuất** (`backend/jobs.py`): `POST /api/jobs` (multipart) → kiểm tra
  magic bytes, 25 MB, 80 trang, đọc chữ bằng pypdfium2, giới hạn 1 job đang
  chạy mỗi người, 4 toàn hệ thống, 10 job/giờ/người → giữ 1 tín dụng → chạy nền →
  `GET /api/jobs/{id}` để thăm dò. Hai tuyến đồng bộ 7.x `POST /api/extract` và
  `POST /api/extract/upload` đi cùng đường ống này nên cùng quy tắc. Job mô hình
  đã trả lời nhưng bị từ chối (thiếu câu trích, sai định dạng) ghi `rejected`
  và **giữ phí**; lỗi phía hệ thống ghi `failed` và **hoàn tự động**; job dở
  dang khi máy chủ khởi động lại cũng hoàn. PDF không ghi xuống đĩa.
- **Tín dụng và chi phí** (`backend/credits.py`): sổ `credit_ledger` chỉ ghi
  thêm là nguồn sự thật, `users.credits_balance` là cache; số dư không âm; khóa
  hàng người dùng khi ghi (`FOR UPDATE` trên Postgres). `llm_calls` ghi token
  vào/ra từ `response.usage` của SDK (adapter `AnthropicEngine` nay có
  `last_usage`, `last_latency_ms`), chi phí ước tính theo bảng giá cấu hình, và
  kết quả (`ok`, `evidence_missing`, `malformed_output`, `provider_error`).
- **Tuyến mới**: `GET /api/config`, `POST /api/auth/mock-login` (chỉ `mock`),
  `GET /api/me`, `GET /api/me/ledger`, `GET /api/me/export`, `GET/POST /api/jobs`,
  `GET /api/jobs/{id}`, `DELETE /api/studies/{id}` (chỉ bản chưa khóa),
  `GET /api/admin/users`, `POST /api/admin/credits`, `GET /api/admin/usage`.
  `/api/health` thêm `auth_mode`; ở chế độ nhiều người dùng `study_count` là
  `null` (không lộ tổng số bản ghi của mọi tài khoản). `MAIDA_FRONTEND_DIR` cho
  phép backend tự phục vụ bản build giao diện (một tiến trình, dùng cho e2e).
- **Giao diện** (`frontend/`): màn hình đăng nhập (liên kết e-mail hoặc Google
  qua Supabase; chế độ thử nhập e-mail là vào), bảng điều khiển (tín dụng, số
  bản ghi, job gần đây tự làm mới), trích xuất qua job có thăm dò và thông báo
  từ chối/hoàn phí, thẻ Tài khoản (số dư, lịch sử tín dụng, tải toàn bộ dữ liệu
  JSON, đăng xuất; với admin: cấp tín dụng, tổng chi phí mô hình, danh sách tài
  khoản), chuyển Anh/Việt cho phần điều hướng và các màn hình mới. Ô khóa quản
  trị chỉ còn ở chế độ `admin_key`. Bản build mặc định gọi API cùng gốc.
- **Triển khai**: `docker-compose.cloud.yml` (Caddy TLS tự động + backend +
  frontend), `deploy/Caddyfile` (HSTS, CSP), `deploy/.env.cloud.example`,
  `deploy/install.sh` (Ubuntu, một lệnh), `DEPLOY_CLOUD.md` (tiếng Việt).
  `backend/check_cloud.py` kiểm tra cấu hình trước khi mở dịch vụ (Postgres,
  JWKS/secret Supabase, khóa mô hình, chế độ mock/demo); bộ cài chạy nó trước
  `docker compose up` và dừng khi có mục hỏng.
- **Kiểm thử**: 25 test mới (`backend/tests/test_800_cloud_multiuser.py`): xác
  minh JWT (hợp lệ, hết hạn, sai aud, chữ ký giả, HS256), tách dữ liệu, quy tắc
  tín dụng, job bất đồng bộ, giới hạn tốc độ, khôi phục job dở dang, di trú tệp
  7.x; 79 test cũ và smoke test Defense App giữ nguyên và vẫn đạt. Kiểm thử
  đầu cuối bằng trình duyệt (`backend/tests/e2e/run_e2e.py`, Playwright): đăng
  nhập → tải PDF → job xong → bị từ chối giữ phí → duyệt → khóa → xuất CSV →
  tài khoản → người thứ hai không thấy gì → admin cấp tín dụng → tiếng Việt.
- **Bảo mật: đóng REST API của Supabase với các bảng M-AIDA** (migration
  `0002_lock_down_data_api`). Trên Supabase, bảng tạo trong `public` mặc định
  được cấp toàn quyền cho `anon` và `authenticated`, và khóa anon là công khai;
  không có migration này, bất kỳ ai cũng đọc được e-mail người dùng và sửa số
  dư tín dụng qua `https://<ref>.supabase.co/rest/v1/...` (đã tái hiện trên
  Postgres 16 với quyền mặc định giống Supabase). Migration thu hồi mọi quyền
  của hai vai trò đó trên mọi bảng và sequence, bật row level security không
  policy; backend là chủ bảng nên không bị ảnh hưởng; trên Postgres không có
  các vai trò này (tự cài) chỉ bật RLS. `check_cloud.py` xác minh trên cơ sở
  dữ liệu thật (RLS, quyền, chủ bảng); `deploy/install.sh` chạy lại kiểm tra
  sau lần khởi động đầu. Sửa đặc tả v8, vốn ghi "chưa cần RLS".
- **Kiểm thử trên Postgres thật**: `MAIDA_TEST_PG_URL` cho mỗi test một cơ sở
  dữ liệu mới nhân từ mẫu có vai trò và quyền mặc định như Supabase; 16 test
  nhiều người dùng và 3 test riêng (`test_803_postgres.py`: danh sách bảng của
  0002 phủ toàn bộ lược đồ, quyền và RLS sau migration, JSONB/tiếng Việt/múi
  giờ/khóa sổ tín dụng) đạt trên Postgres 16.
- **Phê duyệt là của con người** (`pi_approved_at`, mới trong `ExtractedEffect`):
  `requires_verification` chỉ là cờ của máy (tin cậy dưới ngưỡng). PATCH
  `/verify` với `pi_approved=true` nay ghi thời điểm phê duyệt; `POST /lock`
  từ chối (422) bản ghi chưa có phê duyệt của người dù máy tin cậy 1,0; đánh
  dấu trích xuất lại (`pi_approved=false`) xóa phê duyệt. Bản ghi 7.x chưa
  khóa cần được duyệt lại một lần. CSV có thêm cột `pi_approved_at`.
- **Giao diện theo bản thiết kế 02/10** (giai đoạn 1): hệ màu kem/hổ phách,
  chữ Source Serif 4 và JetBrains Mono tự lưu trong gói (fontsource, không
  CDN); thanh đầu với biểu tượng khóa, thẻ điều hướng, một viên trạng thái
  thay dải bốn ô, viên tín dụng, chữ cái đầu tài khoản, chuyển EN/VI; màn
  hình **Kiểm chứng ba cột** (`ReviewScreen`): hàng chờ lọc Tất cả/Cần kiểm
  chứng/Đã duyệt/Đã khóa với ký hiệu ◇/◆, cột bằng chứng hiện câu trích
  nguyên văn và số trang cho thống kê và cỡ mẫu kèm phép quy đổi (không hiện
  trang PDF vì không giữ PDF), bảng Field/Machine/Current trong đó cột máy
  không bao giờ đổi, biến điều tiết dạng nút chọn, ghi chú bắt buộc trước khi
  duyệt, khóa phải gõ lại mã nghiên cứu, phím tắt J/K/A/L; bảng điều khiển có
  thẻ "N bản ghi đang chờ, tiếp theo là…" mở thẳng bản ghi; trang Trích xuất
  hai cột với bốn bước quy trình (đọc văn bản, nhận diện, quy đổi, cổng bằng
  chứng) ánh xạ từ trạng thái job; thẻ Bộ dữ liệu riêng (đếm, thanh tiến độ
  khóa, CSV, Notion); màn hình đăng nhập hai cột. Không có nhân vật minh họa.
  Bỏ `StatusBanner` và `VerificationDashboard` cũ. Giai đoạn 2: **forest plot
  xem trước** trong Bộ dữ liệu (`ForestPlot`): mỗi bản ghi đã khóa một dòng,
  khoảng tin cậy 95% tính trên Fisher z từ `variance_z` của máy chủ (hoặc
  1/(n−3) khi thiếu) rồi đổi về r, ô vuông theo trọng số nghịch phương sai,
  hình thoi gộp theo hiệu ứng cố định ghi rõ "xem trước" vì mô hình ba cấp
  chạy ở metafor; **tour hướng dẫn** 11 bước dạng hộp chữ song ngữ (tự mở lần
  đăng nhập đầu, nút "Guide/Hướng dẫn" mở lại), đánh dấu vùng liên quan trên
  từng màn hình. **Bản đồ Việt Nam chìm dưới nền** như trang 7.x
  (`frontend/src/assets/vnmark.svg`, 5,6 KB): đường bờ đất liền, quần đảo
  Hoàng Sa và Trường Sa, lá cờ ở cực Bắc, ngôi sao ở Cần Thơ, bốn ngọn hải
  đăng nhấp nháy (dừng khi người dùng chọn giảm chuyển động); rõ ở cột trái
  màn hình đăng nhập, mờ dưới nội dung ở mọi trang khác, không in ra. Hai ảnh
  chân dung trong bản đồ cũ được bỏ theo quyết định không dùng nhân vật.
- **Mặt tiền theo gói thiết kế 03/10** (quyết định cùng ngày: nhân vật ở mặt
  tiền, không ở bàn làm việc). Cột trái màn hình đăng nhập có tranh minh họa
  hai tác giả (`frontend/src/assets/people/scene-login.webp`, 37 KB, giữ tỉ lệ
  gốc, không cắt); bản đồ Việt Nam chìm chuyển sang sau cột biểu mẫu. Hộp
  **Liên hệ** (`ContactDialog`), mở từ chân trang đăng nhập và chân trang ứng
  dụng: Đỗ Thùy Hương và PGS.TS. Phan Anh Tú (ảnh đại diện, vai trò đồng sáng
  lập, e-mail, GitHub, trang cá nhân; Thầy đã đồng ý), M-AIDA trình bày là dự
  án nghiên cứu luận án, không ghi địa chỉ Trường, không ghi chức vụ hành chính.
  Chân trang bỏ dòng "School of Economics, Can Tho University". Nguồn và quyền
  dùng hình ghi ở `frontend/src/assets/people/README.md`. Không đưa vào: nhân vật
  trong tour, thẻ mẹo, hộp khóa và công cụ quản trị; trang Tạo tài khoản có thêm
  trường và trang Bảng giá (để sau beta). Kiểm thử đầu cuối mở hộp Liên hệ và
  kiểm tra không có địa chỉ, chức vụ.
- **Tranh đăng nhập luân phiên** (ảnh cô gửi 03/10): mỗi lần mở trang hiện một
  trong ba tranh cùng cỡ 688 × 384 (hai tác giả trước màn hình phân tích; hai tác
  giả cầm kính lúp; Hương với biểu tượng M-AIDA), mỗi tranh có mô tả thay thế
  riêng. Ảnh đại diện trong hộp Liên hệ là ảnh nhìn thẳng, cùng cỡ đầu, cùng áo
  dài trắng như hai nhân vật trong logo 3D.
- **Danh sách mời cho beta kín** (`MAIDA_INVITED_EMAILS`): trước đây ai có
  đường dẫn cũng đăng nhập được (bằng Google, hoặc thư đăng nhập khi đã có SMTP)
  và mỗi tài khoản mới nhận tín dụng miễn phí trả bằng khóa API của người vận
  hành. Nay chỉ địa chỉ hoặc tên miền (`@ctu.edu.vn`) trong danh sách, cùng các
  admin, mới đăng nhập được; để trống là chỉ admin; `*` là mở cho mọi người.
  Kiểm tra ở mọi yêu cầu, trước khi ghi gì vào cơ sở dữ liệu, nên người ngoài
  danh sách không tạo được tài khoản và bỏ một địa chỉ khỏi danh sách là khóa
  ngay tài khoản đó. Giao diện hiện một màn hình "chưa có trong danh sách beta"
  kèm địa chỉ liên hệ thay vì không gian làm việc toàn lỗi. `check_cloud.py`
  báo số địa chỉ, tên miền được mời và cảnh báo khi để `*`. Chế độ "Testing"
  của Google OAuth không thay được việc này: với quyền đăng nhập cơ bản, người
  ngoài danh sách thử nghiệm vẫn đăng nhập được.
- **Chạy thử một mình trên Windows** (`CHAY_MAIDA_V8_THU.bat`): bản 8.0 ở chế độ
  thử trên `127.0.0.1:8766`, môi trường Python và cơ sở dữ liệu riêng, mã khóa
  lấy từ bản 7.2.3 bên cạnh; không cần Supabase, VPS, tên miền hay SMTP.
- **Logo 3D** (`Logo3D`, `src/three/maidaLogo3d.ts`, dựng lại từ bản thiết kế
  03/10): chữ ba lớp mực/cát/hổ phách như mô hình ba cấp, gạch nối là một dòng
  forest plot, bản đồ Việt Nam với Hoàng Sa, Trường Sa và Cần Thơ là hình thoi
  gộp, hai tác giả đứng hai đầu. Ở cột trái màn hình đăng nhập (kéo để xoay, bánh
  xe vẫn cuộn trang) và trong hộp "M-AIDA 3D" mở khi bấm logo ở đầu trang (có
  phóng to). three.js 0.184.0 cài trong gói, tách thành chunk riêng (~145 KB
  gzip) chỉ tải ở hai chỗ đó; không gọi CDN nên không phải nới CSP. Không có
  WebGL thì hiện logo phẳng; khi người dùng chọn giảm chuyển động thì mô hình
  đứng yên. Khung hình tính theo bán kính ngang của mô hình để không bị cắt ở
  mọi góc xoay. Kiểm thử đầu cuối kiểm tra cả hai chỗ.
- **Pháp lý**: `legal/TERMS.md` và `legal/PRIVACY.md` (Điều khoản dịch vụ và
  Chính sách riêng tư cho beta kín, song ngữ Anh/Việt, viết đối chiếu được với
  lược đồ `backend/db.py`: không lưu PDF, các bảng lưu gì, bên xử lý Supabase/
  Anthropic/VPS, quyền xuất và xóa, luật Việt Nam, tòa Cần Thơ); sinh trang tĩnh
  `/legal/terms.html`, `/legal/privacy.html` bằng `legal/build_pages.py`; liên
  kết từ màn hình đăng nhập và chân trang ở chế độ nhiều người dùng.
- **Gói chạy kiểm định độ chính xác** (`validation/`), chưa có kết quả nào:
  `run_benchmark.py` chạy đúng đường trích xuất của ứng dụng một lần trên mẫu
  đã khóa (từ chối khung `PROVISIONAL`, temperature chưa đóng băng, `LLM_MODEL`
  trống, cây git có thay đổi chưa commit; không ghi đè thư mục chạy; chạy tiếp
  sau gián đoạn chỉ khi cấu hình trùng `run_config.json`; thử lại chỉ khi lỗi
  nhà cung cấp) và ghi `run_manifest.json`, `proposals.csv` (đề xuất máy nguyên
  vẹn), câu trả lời thô, CSDL để PI kiểm chứng trong ứng dụng, cùng hai mẫu
  `proposal_matches.csv` và `verification_log.csv`. `coding_workbooks.py` tạo
  sổ liệt kê candidate effect và hai sổ Excel cho hai người mã hóa (cột định
  danh khóa, danh sách chọn, kiểm tra r trong [-1, 1], N nguyên dương), rồi
  gộp thành `gold_standard_draft.csv` (chỉ điền sẵn khi hai người đồng ý) và
  `disagreements.csv`. `build_predictions.py` ghép một đợt chạy với chuẩn vàng
  đã phân xử thành `predictions.csv` theo quy tắc ghi sẵn (một đề xuất mỗi bài;
  mọi đề xuất phải được ghép; từ chối đợt diễn tập và đợt còn lỗi).
  `analyze_validation.py`: đề xuất có r nhưng thiếu N tính là N sai thay vì
  làm hỏng phân tích. Bản nháp sửa §6 protocol: `validation/PROTOCOL_S6_DRAFT_VI.md`.
- **Đóng băng cấu hình mô hình**: `LLM_TEMPERATURE` (tùy chọn; để trống thì
  không gửi tham số, đúng hành vi cũ); `extractor.prompt_fingerprint()` băm
  system prompt, mẫu tin nhắn, giới hạn 40.000 ký tự và 1.024 token đầu ra
  (hiện `sha256:fb368e1cb9123eef`; prompt của 8.0 trùng 7.2.x, khác 7.1.1).
- Phụ thuộc mới: `sqlalchemy`, `psycopg[binary]`, `alembic`, `PyJWT[crypto]`
  (backend); `openpyxl` (chỉ cho `validation/`, `validation/requirements.txt`);
  `three` 0.184.0 (frontend, logo 3D, chỉ tải ở đăng nhập và hộp logo);
  `axios` nâng lên 1.20 (vá lỗ hổng mức cao của 1.0 đến 1.19 do `npm audit` báo:
  prototype pollution trong fetch adapter, ReDoS khi phân tích URL `data:`);
  `@supabase/supabase-js` (frontend, chỉ tải khi chạy chế độ
  `supabase`). Chưa có trong 8.0: thanh toán, trang giá, xóa tài khoản tự phục
  vụ, Sentry/uptime (xem `DEPLOY_CLOUD.md` §8).

## 7.2.3 (02/10/2026): sửa lỗi mã PIN của Defense App; chạy thật trên Windows

- **Sửa lỗi** `demo/ui.html`: từ 7.2.0 (Defense App v1, 01/08/2026) nút *Presenter
  PIN* gọi hàm `presenterPin()` chưa được định nghĩa và giao diện không gửi tiêu đề
  `X-MAIDA-Demo-PIN`, nên mọi thao tác ghi qua giao diện (trích xuất, duyệt, khóa,
  reset) đều bị `demo/run_defense.py` trả về 401. Nay có hộp nhập PIN trong trang,
  PIN giữ trong `sessionStorage` của phiên và được gửi kèm mọi yêu cầu
  POST/PATCH/PUT/DELETE; sai PIN thì xóa và hỏi lại. Trang nhận `?pin=` trên URL
  (chỉ dành cho bộ khởi chạy cục bộ) rồi xóa khỏi thanh địa chỉ.
- `demo/smoke_test.py` thêm kiểm tra tĩnh: giao diện phải định nghĩa `presenterPin`
  và gửi `X-MAIDA-Demo-PIN`, để lỗi này không lặp lại.
- `CHAY_MAIDA_WINDOWS.bat`: chỉ nhận Python 3.12/3.11 **64-bit** (`py -3.12-64`),
  báo rõ khi máy chỉ có bản 32-bit thay vì để pip biên dịch pandas rồi hỏng; tự
  tạo mã PIN 4 chữ số (`MAIDA_DEMO_PIN`) in to ở cuối cửa sổ, mở trình duyệt với
  `?pin=` để không phải gõ lại; đặt sẵn `MAIDA_ADMIN_KEY` để backend không in khóa
  quản trị ra màn hình (dễ nhầm với PIN; ở chế độ demo khóa này không dùng).
- `demo/HUONG_DAN_CHAY_THAT.md` cập nhật theo hai điểm trên. Số hiệu 7.2.3 ở
  `backend/main.py`, `backend/pyproject.toml`, `CITATION.cff`, `.zenodo.json`.
- Không đổi công thức, lược đồ dữ liệu hay bản ghi đã khóa.

## Chưa phát hành: dọn kho và viết lại lịch sử (01/10/2026)

- Kho chỉ còn phần chương trình máy tính và tài liệu kỹ thuật: gỡ các trang web
  giới thiệu/sáng tạo (`*.html` ở gốc kho), `assets/` đa phương tiện (ảnh, bài hát,
  phông chữ), `voice/`, `film/`, `icons/`, `css/`, workflow GitHub Pages và các tài
  liệu làm việc cũ (`CODE_REVIEW_2026-08-31.md`, `TRUOC-CONG-BO.md`,
  `PUBLISHING.md`, `docs/BRANCH-POLICY.md`, `HUONG_DAN_TIENG_VIET.docx`). Giữ
  `assets/brand/` và `assets/diagrams/`.
- Lịch sử Git được viết lại: mọi commit đứng tên `Do Thuy Huong
  <thuyhuongctu@gmail.com>`, bỏ trailer công cụ trong thông điệp commit; mọi mã
  commit thay đổi. Tag `v7.1.1` trỏ lại đúng commit tham chiếu của hồ sơ đăng ký
  quyền tác giả (xem `IP_REGISTER.md`). Chỉ giữ nhánh `main`.
- Không thay đổi mã nguồn backend/frontend/analysis/validation/demo.

## Chưa phát hành: gỡ PyMuPDF (AGPL-3.0) khỏi phụ thuộc runtime (29/09/2026)

- Thay PyMuPDF bằng **pypdfium2** (BSD-3-Clause / Apache-2.0) tại đúng một
  điểm dùng: `backend/main.py`, hàm `extract_pdf` (tuyến `POST /api/extract`).
  Xem `THIRD_PARTY_LICENSES.md` mục 2 để biết lý do và phạm vi.
- Kiểm thử (`backend/tests/test_persistence_and_demo_mode.py`,
  `backend/tests/test_720_post_extraction.py`) và script lịch sử
  `verify_findings.py` trước đây dùng PyMuPDF để tạo tệp PDF mẫu; nay dựng PDF
  tối giản trực tiếp bằng tay (không phụ thuộc thư viện tạo PDF nào), tránh
  đưa PyMuPDF trở lại qua đường kiểm thử.
- Đồng bộ `license` trong `backend/pyproject.toml` (trước đó ghi
  `LicenseRef-MAIDA-Academic`, không khớp `LICENSE`) thành `AGPL-3.0-only` —
  bản chuẩn `LICENSE` gốc không đổi, chỉ sửa siêu dữ liệu gói.
- Không hồi tố: gói lưu chiểu `MAIDA_SOURCE_DEPOSIT_v7.1.1_SANITIZED.zip` đã
  nộp cho hồ sơ đăng ký quyền tác giả 7.1.1 giữ nguyên, vẫn dùng PyMuPDF như đã
  khai; thay đổi này chỉ áp dụng cho mã nguồn từ 7.1.2 trở đi.

## [7.2.2] - 2026-09-23: khóa quản trị cho mọi yêu cầu ghi qua API

Bản vá bảo mật sau 7.2.1, không đổi công thức, không đổi lược đồ dữ liệu, không
đụng bản ghi đã khóa. Mã đã vào `main` qua PR #103; bản này chỉ gắn số hiệu để
dựng lại ảnh container có kèm bản vá.

- Bảo mật: nginx của bản triển khai chính chuyển mọi yêu cầu `/api/` sang
  backend, nên trước bản này khách ghé bất kỳ có thể gọi thẳng
  `PATCH /verify`, `POST /lock`, `POST /extract` (tốn ngân sách LLM) và
  `POST /notion/sync`. Nay middleware `admin_key_guard` chặn mọi yêu cầu
  POST/PATCH/PUT/DELETE thiếu header `X-MAIDA-Admin-Key` khớp
  `MAIDA_ADMIN_KEY` (so sánh hằng thời gian); các tuyến chỉ đọc vẫn công
  khai. Không đặt khóa thì backend tự sinh một khóa và in ra lúc khởi động,
  không bao giờ mặc định mở. Defense App (`MAIDA_DEMO_MODE`) giữ PIN riêng.
- Giao diện: ô "Admin key" ở đầu trang, khóa chỉ lưu trong `localStorage`,
  không nhúng vào gói JS lúc build.
- Ảnh `latest` trên GHCR trước bản này dựng từ 7.2.1, chưa có khóa quản trị;
  máy chủ đang chạy ảnh cũ cần kéo lại ảnh và đặt `MAIDA_ADMIN_KEY`.
- DOI: **DOI phiên bản của 7.2.2 là `10.5281/zenodo.22920619`** (tag `v7.2.2`
  = `8af4881`), ghi bổ sung sau khi phát hành. Bản phát hành GitHub lúc đầu
  mang nhầm tag viết hoa `V7.2.2`, nên Zenodo lưu thêm một bản ghi trùng,
  `10.5281/zenodo.22920581`, cùng commit `8af4881`: nội dung đúng nhưng KHÔNG
  trích dẫn, để mọi trích dẫn trỏ về một bản ghi. Tag viết hoa cũng không kích
  hoạt `deploy-ghcr.yml` (bộ lọc `v*` phân biệt hoa thường); ảnh GHCR 7.2.2 chỉ
  được dựng sau khi gắn lại tag `v7.2.2`.

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
