# M-AIDA 8.0: chạy thử nội bộ cho nhóm nhỏ

**Cách chạy:**
- Máy chủ chạy trên laptop của chị.
- Người được mời vào bằng một đường link qua đường hầm Cloudflare. Laptop phải bật thì link mới hoạt động.
- Mỗi người đăng nhập bằng e-mail và mật khẩu do chị tạo. Hệ thống không gửi thư nên không cần dịch vụ gửi thư.
- Trích xuất dùng Claude thật, tính tiền vào khóa API của chị. Thanh toán tắt.

**Ba lớp chặn người lạ:**
1. Không ai tự đăng ký được, vì chị tắt chức năng đăng ký trong Supabase.
2. Chỉ người có tài khoản do chị tạo mới đăng nhập được.
3. Chỉ e-mail có trong `noi_bo.env` mới dùng được M-AIDA. Người có tài khoản nhưng không có tên trong danh sách sẽ thấy màn hình "chưa có trong danh sách".

---

## A. Làm một lần

### 1. Supabase (dự án M-AIDA, `cdpsggkiiovciqsdavka`)

1. **Authentication → Sign In / Providers:**
   - Email: **bật**;
   - "Allow new users to sign up": **tắt**.
2. **Authentication → Users → Add user → Create new user**, làm cho từng người:
   - nhập e-mail và mật khẩu;
   - đánh dấu **Auto Confirm User**;
   - tạo cả tài khoản của chị (thuyhuongctu@gmail.com).
3. **Project Settings → API Keys:** chép **Publishable key** (bắt đầu bằng `sb_publishable_`).
   - **Không** dùng Secret key (`sb_secret_`): bộ chạy sẽ từ chối, vì khóa ở ô này được gửi tới mọi trình duyệt.

### 2. Anthropic
Ở console.anthropic.com → Settings → Limits, đặt **hạn mức chi tiêu tháng**, ví dụ 20 USD. Mỗi bài trích xuất tốn vài cent. Hạn mức để chặn trường hợp ngoài ý muốn.

### 3. Cloudflared (công cụ mở đường link)
Mở PowerShell, dán lệnh sau rồi nhấn Enter:

```
winget install --id Cloudflare.cloudflared
```

Cài xong, đóng PowerShell.

### 4. Thư mục `M-AIDA-noi-bo`
1. Giải nén gói vào `Claude-Workspace\projects\phan-mem-games\M-AIDA-noi-bo`, cạnh thư mục `M-AIDA`.
   - Thư mục `M-AIDA` giữ mã khóa Claude trong `backend\.env`; bản nội bộ đọc khóa từ đó.
2. Chép `noi_bo.env.mau` thành `noi_bo.env` rồi mở bằng Notepad:
   - dán Publishable key vào dòng `SUPABASE_ANON_KEY=`;
   - ở dòng `MAIDA_INVITED_EMAILS=`, ghi e-mail những người được mời, cách nhau bởi dấu phẩy, ví dụ `thuyhuongctu@gmail.com, patu@ctu.edu.vn`;
   - lưu lại.

---

## B. Mỗi lần chạy thử

1. **Mở máy chủ:** nhấp đúp `CHAY_MAIDA_NOI_BO.bat`.
   - Lần đầu, bộ chạy cài môi trường Python mất vài phút.
   - Bộ chạy tự kiểm tra cấu hình. Nếu có dòng `[LOI ]` thì sửa `noi_bo.env` theo lời nhắn.
   - Trình duyệt mở `http://127.0.0.1:8767/`. Chị đăng nhập để kiểm tra.
2. **Mở đường link:** nhấp đúp `MO_LINK_NOI_BO.bat`.
   - Trong cửa sổ hiện ra, tìm dòng có `https://....trycloudflare.com`. Đó là đường link cho nhóm.
3. **Gửi cho từng người, riêng tư (ví dụ Zalo nhắn riêng):** đường link, e-mail và mật khẩu của họ. Mỗi lần mở lại, link sẽ khác.
4. **Trong lúc chạy thử:**
   - Giữ laptop bật và **không cho máy ngủ**: Settings → System → Power → Screen and sleep → "Never" khi cắm sạc.
   - Không đóng hai cửa sổ đen.
5. **Kết thúc:** đóng cửa sổ đường link trước, rồi đóng cửa sổ máy chủ.

## C. Quản lý trong lúc thử
- **Tín dụng:** mỗi tài khoản mới có 10 tín dụng (1 tín dụng = 1 bài PDF). Chị cấp thêm trong mục **Công cụ vận hành → Cấp tín dụng** của ứng dụng (chỉ tài khoản quản trị thấy mục này).
- **Thêm người:** tạo tài khoản trong Supabase, thêm e-mail vào `noi_bo.env`, rồi đóng và mở lại `CHAY_MAIDA_NOI_BO.bat`.
- **Gỡ người:** xóa e-mail khỏi `noi_bo.env` rồi mở lại. Người đó bị chặn ngay, còn dữ liệu của họ vẫn giữ.
- **Dữ liệu:** nằm trong `backend\maida_noi_bo.db`. Muốn sao lưu thì tắt M-AIDA rồi chép tệp này. Tệp PDF không bị ghi xuống đĩa.
- **Chi phí:** mục Công cụ vận hành có bảng chi phí ước tính; số tiền thật xem trên console Anthropic.

## D. Lưu ý
- **Giao diện:** mặc định là Vũ trụ 3D. Nút tròn cạnh nút "✦ Vũ trụ" đổi trời Pastel và trời Tối. Bấm "✦ Vũ trụ" để về giao diện Giấy, nhẹ hơn cho máy yếu.
  - Máy không có WebGL tự dùng nền 2D.
  - Người bật "giảm chuyển động" trong hệ điều hành chỉ thấy khung tĩnh.
- **Không đổi `MAIDA_AUTH_MODE` sang `mock`** khi đang mở link. Ở chế độ mock, ai nhập e-mail bất kỳ cũng vào được.
- Nhắc người dùng thử **không tải tài liệu mật**: nội dung PDF được gửi tới Anthropic để trích xuất.
- Đây là chạy thử nội bộ, không thu tiền. Việc bán vẫn chờ Giấy chứng nhận, văn bản đồng ý của ba bên và kết quả đánh giá độ chính xác.
- Muốn có link cố định hoặc chạy cả khi tắt laptop thì chuyển sang máy chủ VPS (xem `DEPLOY_CLOUD.md`).
- Bản 7.2.3 (cổng 8765) và bản chạy thử một mình (cổng 8766) vẫn dùng được song song.
