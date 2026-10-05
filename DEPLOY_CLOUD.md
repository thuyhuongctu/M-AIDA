# Triển khai M-AIDA 8.x dạng dịch vụ web nhiều người dùng (beta kín)

Tài liệu này dành cho người vận hành (Đỗ Thùy Hương). Bản 8.x giữ nguyên lõi
khoa học của 7.2 (trích xuất có cổng bằng chứng, dẫn xuất phương sai, quy
trình duyệt và khóa) và bọc thêm: đăng nhập theo từng người dùng, tách dữ liệu
theo chủ sở hữu, job trích xuất chạy nền, sổ tín dụng và nhật ký chi phí mô
hình. Bộ chạy Windows (`CHAY_MAIDA_WINDOWS.bat`) và Defense App vẫn chạy như
cũ ở chế độ một người dùng (`MAIDA_AUTH_MODE=admin_key`, mặc định).

## 1. Kiến trúc

```
Trình duyệt ──HTTPS──> Caddy (TLS tự động cho MAIDA_DOMAIN)
                         ├── /        → frontend (nginx, React)
                         └── /api/*   → backend (FastAPI)
                                          ├── Supabase Auth  (xác minh JWT bằng JWKS, không gọi Supabase mỗi yêu cầu)
                                          ├── Supabase Postgres (users, studies, extraction_jobs, llm_calls, credit_ledger, audit_log)
                                          └── Anthropic API (khóa chỉ ở máy chủ)
```

Ba container chạy trên một VPS 2 vCPU / 4 GB. Dữ liệu người dùng nằm ở Postgres
của Supabase (sao lưu hằng ngày theo gói); PDF tải lên chỉ ở bộ nhớ trong lúc
đọc chữ, không ghi xuống đĩa.

## 2. Chuẩn bị (làm một lần)

1. **VPS** Ubuntu 22.04/24.04 đặt ở **Singapore** (cùng vùng với cơ sở dữ liệu
   Supabase `ap-southeast-1`, để mỗi yêu cầu không phải đi xa). Tối thiểu
   2 vCPU / 2 GB; nên 2 vCPU / 4 GB vì bước dựng giao diện (npm) chạy ngay trên
   máy chủ.
2. **Tên miền** (hoặc tên miền con) trỏ bản ghi A về IP của VPS.
3. **Máy chủ gửi thư (SMTP) cho thư đăng nhập: bắt buộc.** Dịch vụ thư có sẵn
   của Supabase chỉ gửi tới địa chỉ của thành viên dự án và chỉ 2 thư mỗi giờ,
   nên người dùng beta sẽ nhận lỗi "Email address not authorized". Tạo tài khoản
   ở một nhà cung cấp SMTP (ví dụ Resend: gói miễn phí 100 thư/ngày; Brevo: 300
   thư/ngày), xác minh tên miền gửi (bản ghi SPF, DKIM do nhà cung cấp đưa), rồi
   điền máy chủ, cổng, tài khoản, mật khẩu ở Supabase → Authentication → Emails →
   SMTP Settings. Địa chỉ gửi nên là `no-reply@<tên miền>`.
4. **Dự án Supabase riêng** cho M-AIDA (không dùng chung với BizOn):
   - Authentication → Providers: bật Email (magic link) và Google (cần OAuth
     client trên Google Cloud; có thể để sau, magic link là đủ cho beta).
   - Authentication → URL Configuration: Site URL = `https://<tên miền>`,
     thêm `https://<tên miền>/**` vào Redirect URLs.
   - Project Settings → API Keys: lấy **Project URL** và khóa **publishable/anon**.
   - Project Settings → Database → Connection string → *Transaction pooler*
     (cổng 6543): lấy chuỗi kết nối, thay tiền tố `postgresql://` bằng
     `postgresql+psycopg://`.
   - Nếu dự án còn ký JWT bằng *JWT secret* (HS256) thay vì khóa bất đối xứng:
     lấy secret ở Project Settings → JWT Keys và điền `SUPABASE_JWT_SECRET`.
5. **Khóa Anthropic** riêng cho dịch vụ, đặt hạn mức chi tiêu tháng trên
   console (gợi ý: bằng khoảng 2 lần doanh thu tín dụng kỳ vọng).

## 3. Cài đặt trên VPS (Ubuntu 22.04/24.04)

Bản 8.0 nằm ở nhánh `v8-cloud` (nhánh `main` vẫn là 7.2.3, bản chạy trên
Windows), nên bộ cài lấy từ nhánh đó và đặt `MAIDA_BRANCH=v8-cloud`:

```bash
ssh root@<ip>
curl -fsSL https://raw.githubusercontent.com/thuyhuongctu/M-AIDA/v8-cloud/deploy/install.sh -o install.sh
MAIDA_BRANCH=v8-cloud bash install.sh   # lần 1: cài Docker, clone kho, tạo deploy/.env.cloud rồi dừng
nano /opt/m-aida/deploy/.env.cloud      # điền MAIDA_DOMAIN, SUPABASE_URL, SUPABASE_ANON_KEY, DATABASE_URL, LLM_API_KEY, MAIDA_ADMIN_EMAILS
MAIDA_BRANCH=v8-cloud bash install.sh   # lần 2: dựng và chạy
```

Khi 8.0 được gộp vào `main`, bỏ `MAIDA_BRANCH` và đổi `v8-cloud` trong đường
dẫn thành `main`.

Lần chạy thứ hai, trước khi khởi động, bộ cài chạy `backend/check_cloud.py`
bên trong image backend: đọc `.env.cloud`, thử kết nối Postgres, tải JWKS của
dự án Supabase (hoặc kiểm tra `SUPABASE_JWT_SECRET`), gọi thử mô hình 5 token,
và in từng mục ĐẠT/HỎNG kèm cách sửa. Có mục HỎNG thì không khởi động. Chạy
lại riêng lúc nào cũng được:

```bash
cd /opt/m-aida
docker compose -f docker-compose.cloud.yml --env-file deploy/.env.cloud run --rm --no-deps backend python check_cloud.py
```

Kiểm tra sau khi chạy: `https://<tên miền>/api/health` trả về
`"auth_mode": "supabase"`, `"storage": "postgres"`, `"llm_ready": true`. Bảng
được tạo tự động khi backend khởi động (Alembic `upgrade head`).

Tài khoản trong `MAIDA_ADMIN_EMAILS` đăng nhập lần đầu sẽ có vai trò
`admin`: thẻ **Account** có công cụ cấp tín dụng và tổng chi phí mô hình.

**Danh sách mời (beta kín).** `MAIDA_INVITED_EMAILS` liệt kê ai được đăng nhập:
từng địa chỉ, hoặc cả tên miền viết với `@` đứng đầu, cách nhau bằng dấu phẩy
(ví dụ `ncs01@gmail.com, @ctu.edu.vn`). Để trống thì chỉ các admin vào được;
`*` thì ai có đường dẫn cũng vào được (chỉ dùng khi đã mở bán, vì mỗi tài khoản
mới nhận tín dụng miễn phí trả bằng khóa API của cô). Người ngoài danh sách bị
từ chối trước khi tài khoản được tạo, và bỏ một địa chỉ khỏi danh sách thì tài
khoản đó bị khóa ngay ở yêu cầu kế tiếp (bản ghi vẫn còn trong cơ sở dữ liệu).
Sửa danh sách xong thì khởi động lại backend:
`docker compose -f docker-compose.cloud.yml --env-file deploy/.env.cloud up -d backend`.

## 4. Vận hành hằng ngày

| Việc | Lệnh / nơi làm |
|---|---|
| Xem log | `cd /opt/m-aida && docker compose -f docker-compose.cloud.yml --env-file deploy/.env.cloud logs -f backend` |
| Cập nhật phiên bản | `bash /opt/m-aida/deploy/install.sh` (pull + build + restart) |
| Cấp tín dụng cho người dùng | Account → Operator tools, hoặc `POST /api/admin/credits` |
| Xem chi phí mô hình | Account → Operator tools (30 ngày), hoặc `GET /api/admin/usage?days=90` |
| Đổi mô hình | sửa `LLM_MODEL` trong `deploy/.env.cloud`, ghi CHANGELOG, restart; kết quả đánh giá độ chính xác chỉ có giá trị với mô hình đã đánh giá |
| Sao lưu | Supabase sao lưu hằng ngày (gói Free giữ 7 ngày từ 2026); kiểm tra khôi phục mỗi quý |
| Xuất dữ liệu một người dùng | người dùng tự bấm *Download all my data (JSON)* ở thẻ Account |
| Nhóm nghiên cứu | người dùng tự làm ở thẻ Team; người được mời phải có trong `MAIDA_INVITED_EMAILS` trước |

Quy tắc tín dụng (xem `backend/credits.py`): mỗi job trừ 1 tín dụng khi được
nhận; job mà mô hình đã trả lời nhưng bị cổng bằng chứng hoặc kiểm tra định
dạng từ chối (422) **không hoàn**; job lỗi phía hệ thống (nhà cung cấp,
timeout, lỗi nội bộ, máy chủ khởi động lại) **hoàn tự động**. Số dư không bao
giờ âm.

Nhóm (thẻ Team, `backend/team.py`): chủ mời tối đa 10 người vào không gian
của mình. Thành viên tải PDF lên bằng tín dụng của chủ và được duyệt, sửa bản
ghi; chỉ chủ khóa, xóa, xuất và sửa PRISMA. Giới hạn job tính theo từng người.
`audit_log` của chủ ghi `by_email` cho mọi việc thành viên làm. Gỡ một người ở
thẻ Team là không gian đóng với họ ngay; bản ghi giữ nguyên.

### Bán gói tín dụng qua payOS (tắt mặc định)

Backend có sẵn luồng mua gói tín dụng trả trước qua payOS (chuyển khoản
VietQR). Mặc định tắt: khi `MAIDA_PAYMENTS` trống, thẻ Account không hiện phần
mua gói và các tuyến `/api/payments/*` trả 503 hoặc 404.

Trước khi bật:

1. Các đồng sở hữu duyệt giá gói, rồi đặt `MAIDA_CREDIT_PACKS`
   (`mã:số tín dụng:giá VND`, cách nhau bởi dấu phẩy). Nếu để trống, backend
   dùng giá **nháp** của kế hoạch 03/10/2026:
   `thu:30:149000,tongquan:100:399000,nhom:300:990000`.
2. Bổ sung điều khoản mua gói vào `legal/TERMS.md` (giá, không hoàn tiền,
   thời hạn dùng tín dụng) rồi sinh lại trang. Thời hạn 12 tháng trong kế
   hoạch **chưa** được backend thực thi: hiện tín dụng không hết hạn.
3. Tạo kênh thanh toán trên payOS gắn với tài khoản ngân hàng nhận tiền, lấy
   Client ID, API Key và Checksum Key.

Cấu hình trong `deploy/.env.cloud`:

```
MAIDA_PAYMENTS=payos
PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...
MAIDA_PUBLIC_URL=https://maida.example.org
```

Chạy `check_cloud.py`: nó báo khóa còn thiếu và in URL webhook. Đăng ký URL
`https://<tên miền>/api/payments/payos/webhook` cho kênh thanh toán trên
trang quản lý payOS, hoặc gọi API (payOS gửi một lượt thử, backend trả 200):

```bash
curl -X POST https://api-merchant.payos.vn/confirm-webhook \
  -H "x-client-id: $PAYOS_CLIENT_ID" -H "x-api-key: $PAYOS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhookUrl":"https://maida.example.org/api/payments/payos/webhook"}'
```

Luồng mua:

1. Người dùng chọn gói; backend ghi đơn `pending` rồi xin payOS một liên kết
   thanh toán (mã đơn 12 chữ số; nội dung chuyển khoản `MA` + 7 số cuối của mã
   đơn; liên kết hết hạn sau `MAIDA_ORDER_TTL_MINUTES`, mặc định 30 phút).
2. Người dùng chuyển khoản trên trang của payOS.
3. payOS gọi webhook kèm chữ ký HMAC-SHA256; backend kiểm chữ ký bằng
   Checksum Key rồi cộng tín dụng.
4. payOS đưa trình duyệt về `/?payment=return&order=...`; thẻ Account hỏi lại
   payOS trạng thái đơn, nên tín dụng vẫn vào khi webhook đến muộn hoặc chưa
   được đăng ký. Người dùng cũng có nút *Check* ở từng đơn.

Bảo đảm của backend:

- mỗi đơn chỉ cộng tín dụng một lần (khóa dòng trên Postgres và chỉ mục duy
  nhất `ux_ledger_purchase_order` của migration `0003_payments`), kể cả khi
  payOS gửi lại webhook;
- chuyển thiếu tiền thì không cộng: đơn giữ trạng thái chờ, ghi
  `UNDERPAID ...` và hiện ở danh sách của người vận hành để xử lý tay;
- tiền đến cho đơn đã hủy hoặc đã hết hạn vẫn được cộng, vì người dùng đã trả;
- tối đa 6 liên kết thanh toán mỗi giờ cho mỗi người;
- hệ thống không tự hoàn tiền.

Người vận hành xem mọi đơn và tổng đã thu ở Account → Operator tools, hoặc
`GET /api/admin/orders`. Giá trị `MAIDA_PAYMENTS=mock` chỉ để kiểm thử (trang
thanh toán giả, không có tiền thật); backend từ chối nó khi đăng nhập thật
(`MAIDA_AUTH_MODE=supabase`).

## 5. Chạy thử không cần Supabase (máy cá nhân hoặc CI)

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && pip install -r requirements.txt playwright
MAIDA_AUTH_MODE=mock MAIDA_FRONTEND_DIR=../frontend/build MAIDA_ADMIN_EMAILS=you@example.org \
  LLM_API_KEY=<khóa thật> uvicorn main:app --port 8765
# mở http://127.0.0.1:8765 → nhập e-mail bất kỳ → có 10 tín dụng
```

Chế độ `mock` dùng token ký cục bộ, chỉ để kiểm thử; đừng mở ra Internet.

Trên Windows có sẵn `CHAY_MAIDA_V8_THU.bat` cho việc này: đặt bản 8.0 (kèm
`frontend\build` đã dựng) trong một thư mục cạnh thư mục `M-AIDA` của bản 7.2.3,
nhấp đúp tệp; nó dựng môi trường Python riêng, lấy mã khóa từ
`..\M-AIDA\backend\.env`, chỉ nghe ở `127.0.0.1:8766` (bản 7.2.3 vẫn ở cổng
8765) và lưu dữ liệu thử ở `backend\maida_v8_thu.db`.
Chạy bộ test nhiều người dùng trên Postgres thật (cần một cơ sở dữ liệu mẫu
`template_supabase` có các vai trò `anon`, `authenticated`, `service_role` và
quyền mặc định như Supabase): `MAIDA_TEST_PG_URL="postgresql+psycopg://postgres@/postgres?host=/tmp/pgtest&port=55432" pytest backend/tests/test_800_cloud_multiuser.py backend/tests/test_803_postgres.py`.
Kiểm thử đầu cuối tự động bằng trình duyệt: `python backend/tests/e2e/run_e2e.py`
(chạy backend giả lập mô hình, đăng nhập, tải PDF, duyệt, khóa, xuất CSV,
kiểm tra tách dữ liệu, mua một gói qua trang thanh toán giả và công cụ vận hành).

## 6. Bảo mật

- **REST API của Supabase phải đóng với các bảng M-AIDA.** Trên Supabase, mọi
  bảng tạo trong schema `public` mặc định được cấp toàn quyền cho vai trò
  `anon` và `authenticated`, và REST API của dự án phục vụ hai vai trò đó cho
  bất kỳ ai có khóa anon, mà khóa này công khai vì trình duyệt cần nó để đăng
  nhập. Migration `0002_lock_down_data_api` (chạy cùng giao dịch với lần tạo
  bảng đầu tiên) thu hồi mọi quyền của hai vai trò đó và bật row level
  security trên tất cả bảng; backend là chủ bảng nên không bị ảnh hưởng.
  `check_cloud.py` kiểm tra lại điều này trên cơ sở dữ liệu thật và bộ cài
  chạy nó ngay sau lần khởi động đầu. Không tạo bảng M-AIDA bằng tay trong
  bảng điều khiển Supabase (bảng sẽ thuộc vai trò khác và thiếu khóa này).
- Bí mật chỉ nằm trong `deploy/.env.cloud` (quyền 600, đã có trong .gitignore).
- Backend xác minh JWT bằng JWKS của dự án (ES256/RS256) hoặc secret HS256;
  kiểm tra `aud`, `exp`; mọi tuyến `/api/*` trừ `/api/health`, `/api/config`
  và webhook payOS đều cần token (webhook được xác thực bằng chữ ký HMAC thay
  cho token); dữ liệu lọc theo `owner_id` ở tầng backend.
- Caddy thêm HSTS, CSP (chỉ cho phép kết nối tới `*.supabase.co`), chặn nhúng iframe.
  Nhạc nền (`frontend/public/audio/`), bài mẫu của bản demo
  (`frontend/public/demo/`) và phông chữ đều đi kèm bản build nên CSP không
  phải mở thêm nguồn nào. Nếu sau này phát nhạc từ website album, thêm
  `media-src 'self' https://thuyhuongctu.github.io` vào CSP.
- Bản demo không cần đăng ký chạy hoàn toàn trong trình duyệt: không gửi yêu
  cầu nào tới `/api`, không gọi mô hình, chỉ đọc bài mẫu tổng hợp.
- Giới hạn: 25 MB và 80 trang mỗi PDF, 1 job đang chạy mỗi người, 4 job toàn
  hệ thống, 10 job mỗi giờ mỗi người (đổi trong `.env.cloud`).
- Nhật ký không ghi nội dung PDF; `audit_log` ghi ai làm gì (extract, verify,
  lock, export, delete, grant) trên bản ghi nào.

## 7. Điều khoản dịch vụ và Chính sách riêng tư

Nguồn là `legal/TERMS.md` và `legal/PRIVACY.md` (song ngữ, bản beta 1.0).
Sửa ở đó rồi chạy `python legal/build_pages.py` để sinh
`frontend/public/legal/terms.html` và `privacy.html`; bản build phục vụ chúng
tại `/legal/terms.html` và `/legal/privacy.html`, được liên kết từ màn hình
đăng nhập ("Khi đăng nhập, bạn chấp nhận…") và chân trang. Trước khi mở beta
cô điền ngày hiệu lực, tên nhà cung cấp VPS (mục 4 của Chính sách) và nên nhờ
người có chuyên môn pháp lý đọc một lượt; thay đổi quan trọng sau đó phải
báo người dùng trước 15 ngày như hai văn bản đã cam kết.

## 8. Chưa có trong 8.0 (dự kiến)

Thanh toán bằng thẻ quốc tế, trang giá công khai, hạn dùng tín dụng 12 tháng,
xóa tài khoản tự phục vụ (hiện
xử lý qua e-mail trong 30 ngày như Chính sách ghi), hàng đợi ngoài tiến trình
(arq + Redis) khi tải tăng, Sentry/uptime.
