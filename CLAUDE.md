# CLAUDE.md: quy tắc làm việc với kho M-AIDA

Tệp này dành cho Claude Code. Claude Code đọc tệp mỗi lần mở kho. Người quyết định mọi việc trong kho là Đỗ Thùy Hương (chủ kho, tác giả chính).

## 1. Dự án
- **M-AIDA** (Meta-Analysis Intelligent Data Assistant). Phần mềm trích xuất cỡ ảnh hưởng (r, n) từ PDF bài báo bằng mô hình ngôn ngữ, có bằng chứng nguyên văn. Người nghiên cứu kiểm chứng rồi khóa bản ghi.
- **Giấy phép:** AGPL-3.0-only.
- **Tác giả:** Do Thuy Huong và Phan Anh Tu (xem `AUTHORS`, `CITATION.cff`).
- **Kho:** https://github.com/thuyhuongctu/M-AIDA
- **Nhánh:**
  - `main`: dòng 7.2.x, bản chạy trên máy Windows.
  - `v8-cloud`: 8.0.0, dịch vụ web nhiều người dùng, beta kín, chạy thử nội bộ.
- Bản 7.1.1 đã đăng ký quyền tác giả (tag `v7.1.1`). Theo `IP_REGISTER.md` mục 6, **không sửa** mã của bản này. Mọi thay đổi đi vào phiên bản mới.

## 2. Danh tính trong commit
- Mọi commit ghi đúng: **`Do Thuy Huong <thuyhuongctu@gmail.com>`**. Toàn bộ lịch sử kho, `AUTHORS` và `CITATION.cff` đều dùng tên này.
- Trước commit đầu tiên của mỗi phiên, chạy:
  - `git config user.name` → phải ra `Do Thuy Huong`;
  - `git config user.email` → phải ra `thuyhuongctu@gmail.com`.
  Nếu khác, dừng lại và báo chị. Không tự sửa cấu hình toàn cục (`--global`).
- **Không dùng** các dạng `DoThuyHuong`, `thuyhuongctu`, `Đỗ Thùy Hương` (có dấu) hay tên khác làm tên tác giả commit. `thuyhuongctu` chỉ là tên tài khoản GitHub, nằm trong đường dẫn kho.
- **Không thêm** dòng `Co-Authored-By`, "Generated with Claude Code" hay đường dẫn phiên vào commit hoặc PR. `.claude/settings.json` đã tắt các dòng này; không bật lại.
- Không dùng `--author`, không sửa tác giả của commit cũ.

## 3. Việc không được làm
1. **Không đọc, in, chép hay commit khóa bí mật**, gồm:
   - `backend/.env`, mọi tệp `*.env` (kể cả `noi_bo.env`);
   - `env.cloud*`, `MAIDA_API_KEY*`;
   - khóa trong biến môi trường.
   Cần biết một biến có được đặt hay không thì hỏi chị, hoặc chạy script kiểm tra có sẵn (`backend/check_llm.py`, `backend/check_noi_bo.py`, `backend/check_cloud.py`).
2. **Không `git push`**, không force-push, không viết lại lịch sử (rebase đã đẩy, filter-repo, sửa tag). Chị tự đẩy.
3. Không xóa tệp khi chị chưa đồng ý. Không ghi ra ngoài thư mục kho. Thư mục thiết kế `../thiet-ke-M-AIDA-cloud-cosmos/` chỉ để đọc.
4. **Không bịa số liệu hay tài liệu tham khảo.** Mọi con số hiện trên giao diện phải có nguồn. Số mẫu phải ghi rõ là số mẫu.
5. Không đổi công thức của lõi khoa học khi chị chưa yêu cầu. Lõi gồm quy đổi r, phương sai, cổng bằng chứng, quy tắc khóa.
6. Không đưa logo hay tên Trường Đại học Cần Thơ, Trường Kinh tế lên giao diện (quyết định 03/10/2026). Giao diện ghi M-AIDA là dự án nghiên cứu.
7. Không mở chế độ đăng nhập `mock` ra Internet. Không tạo bảng Supabase bằng tay; Alembic tạo bảng.
8. Không tải thư viện, phông chữ hay dữ liệu từ CDN lúc chạy (unpkg, jsdelivr, Google Fonts). CSP trong `deploy/Caddyfile` chỉ cho `'self'`. Mọi thứ cài từ npm và đóng gói vào bản build.

## 4. Cách làm việc
- **Trả lời bằng tiếng Việt.** Mã, tên biến và chú thích trong mã viết tiếng Anh như phần còn lại của kho; tài liệu người dùng theo `THUAT_NGU_VA_QUY_TAC_TIENG_VIET.md`.
- Việc từ 3 bước trở lên: hỏi lại chỗ chưa rõ và trình kế hoạch ngắn trước khi sửa. Việc nhỏ thì làm ngay.
- Nói thẳng khi thấy rủi ro: lỗi, mâu thuẫn số liệu, vi phạm quyết định cũ.
- Tài liệu viết câu rõ ràng, không dùng dấu gạch dài (em dash) để nối ý.
- Thay đổi người dùng thấy được: thêm mục vào `CHANGELOG.md`. Thêm thư viện: cập nhật `THIRD_PARTY_LICENSES.md` và kiểm giấy phép tương thích AGPL.
- **Commit message:**
  - tiếng Việt;
  - dòng đầu dạng `8.0.0: <việc đã làm>`;
  - thân là các gạch đầu dòng ngắn.
  Chỉ commit khi chị bảo, hoặc khi kế hoạch chị đã duyệt có bước commit.

## 5. Cấu trúc kho
- `backend/`: FastAPI, SQLAlchemy 2, Alembic (`backend/alembic/`), các job trích xuất.
  - Test: `backend/tests/`.
  - E2E Playwright: `backend/tests/e2e/`.
- `frontend/`: React 19, Vite 6, TypeScript.
  - Mã: `src/components/`.
  - Cảnh 3D của giao diện Vũ trụ: `src/cosmos/`.
  - Chữ giao diện hai thứ tiếng: `src/i18n.ts`.
  - Kiểu dáng: `src/index.css` (token màu, `:root[data-look="cosmos"]`).
- `deploy/`: Docker, Caddy, cấu hình máy chủ.
- `legal/`: điều khoản và chính sách song ngữ.
- `demo/`, `validation/`: bản trình diễn và gói kiểm định độ chính xác.
- Tài liệu chạy: `HUONG_DAN_CHAY_NOI_BO.md` (chạy thử nội bộ), `DEPLOY_CLOUD.md`, `CHAY_MAIDA_*.bat`.

## 6. Lệnh kiểm thử (PowerShell, tại thư mục kho)
Môi trường Python ở `.venv` (do `CHAY_MAIDA_WINDOWS.bat` tạo). Lần đầu cài thêm công cụ kiểm thử:
```
.\.venv\Scripts\python -m pip install pytest ruff playwright
```
Chạy trước mỗi commit:
```
cd backend; ..\.venv\Scripts\python -m pytest -q; cd ..
.\.venv\Scripts\ruff check backend demo validation --select E9,F
cd frontend; npm ci; npx tsc --noEmit; npx vite build; cd ..
```
E2E trình duyệt (chậm, chạy khi đổi giao diện):
```
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python backend\tests\e2e\run_e2e.py
.\.venv\Scripts\python backend\tests\e2e\run_e2e_password.py
```
Không commit khi còn test hỏng. Không sửa test cho khớp với lỗi.

## 7. Giao diện Vũ trụ (thiết kế "M-AIDA Cloud Cosmos")
- **Bản thiết kế gốc:** ở `../thiet-ke-M-AIDA-cloud-cosmos/`, đã khai trong `.claude/settings.json` để đọc được. Đọc `README_THIET_KE.md` trong thư mục đó trước khi chuyển thêm phần nào, vì có danh sách số liệu và DOI chưa được kiểm.
- **Đã chuyển vào app** (commit d5645e4):
  - `cosmos-scene.js` → `frontend/src/cosmos/scene.ts`;
  - `maida-planets.js` → `frontend/src/cosmos/planets.ts`;
  - trạm bay của từng thẻ → `frontend/src/cosmos/stations.ts`;
  - khung React → `frontend/src/components/CosmosScene.tsx`;
  - token màu, kính mờ, phông → `frontend/src/index.css`.
- **Khi chuyển tiếp từ thiết kế:**
  - đóng gói thư viện từ npm;
  - giữ chế độ giảm chuyển động;
  - dừng vẽ khi thẻ trình duyệt bị ẩn;
  - máy không có WebGL dùng nền 2D (`CosmosBackdrop.tsx`);
  - không dùng số liệu P6 hay số không nguồn trong app;
  - không thêm khóa tên miền.
- **Ảnh tác giả:** `frontend/src/assets/people/README.md` ghi nơi được dùng ảnh nhân vật và ảnh chân dung. Theo đúng quy định trong tệp đó.
