# Chạy M-AIDA thật trên máy Windows

Hướng dẫn này để **trích xuất số liệu thật từ tệp PDF** bằng mã khoá Claude
của chính cô. Nó khác với [bản dùng khi bảo vệ](HUONG_DAN_BAO_VE.md): bản bảo
vệ chạy không cần mạng và không gọi AI.

## Cần có

1. **Python 3.12 bản 64-bit** (hoặc 3.11 64-bit). Tải ở
   <https://www.python.org/downloads/windows/>, chọn *Windows installer (64-bit)*.
   Bản 32-bit không dùng được: numpy/pandas/scipy không có gói dựng sẵn, pip sẽ
   cố biên dịch rồi hỏng; tệp `.bat` sẽ dừng và báo nếu máy chỉ có bản 32-bit.
   Khi cài, nhớ đánh dấu ô **"Add python.exe to PATH"**. Đừng dùng 3.13: một
   vài thư viện số của M-AIDA chưa có bản cài sẵn cho 3.13.
2. **Mã khoá Claude (API key)**, bắt đầu bằng `sk-ant-`. Lấy ở
   <https://console.anthropic.com/settings/keys>. Nên đặt luôn **hạn mức chi
   tiêu mỗi tháng** trong mục *Limits* của trang ấy.
3. Bản sao kho M-AIDA trên máy (nút *Code → Download ZIP* trên GitHub, giải nén).

## Chạy

Nhấp đúp **`CHAY_MAIDA_WINDOWS.bat`** ở thư mục gốc của kho.

- **Lần đầu** tệp sẽ cài môi trường Python (vài phút, cần mạng), rồi hỏi mã
  khoá. Dán mã vào và nhấn Enter. Chữ **không hiện ra** trên màn hình khi dán,
  đó là cố ý. Mã được lưu vào `backend\.env` **trên máy cô**. Git bỏ qua tệp
  này, nên mã không bao giờ lên GitHub.
- Trước khi mở app, tệp `.bat` chạy `backend\check_llm.py`: gửi một yêu cầu 5 token
  để xác nhận mã khoá và mã mô hình (`LLM_MODEL`) dùng được. Nếu báo THẤT BẠI, sửa
  `backend\.env` theo gợi ý in ra rồi chạy lại; app chỉ mở khi kiểm tra THÀNH CÔNG.
- **Các lần sau** chỉ cần nhấp đúp; trình duyệt tự mở `http://127.0.0.1:8765/`.
- Cửa sổ đen phải để mở trong lúc làm việc; đóng nó là tắt M-AIDA.
- Khung **MA PIN (Presenter PIN)** trong cửa sổ đen là mã 4 chữ số bảo vệ các
  thao tác ghi. Trình duyệt do tệp `.bat` mở sẽ nhận mã này sẵn (nút góc trên
  hiện "Presenter unlocked"); chỉ khi mở trang bằng tay mới cần bấm *Presenter
  PIN* và nhập. Trước đây (7.2.0 đến 7.2.2) nút này bị lỗi và mọi thao tác ghi
  trả về 401; đã sửa ở 7.2.3. Mã này cần trước khi tải PDF
  lên, sửa hay khoá bản ghi. Mỗi lần chạy một mã mới.

## Quy trình với một bài báo

1. Tải tệp PDF lên. Claude đọc chữ trong PDF và **đề xuất** hệ số ảnh hưởng,
   cỡ mẫu và **câu trích nguyên văn** làm bằng chứng. Đề xuất nào không có câu
   trích khớp với bài thì bị từ chối, không tạo bản ghi.
2. Cô đối chiếu từng con số với bài gốc, sửa nếu cần, rồi **khoá** bản ghi.
3. Xuất CSV khi đã khoá xong.

## Giới hạn cần biết

- PDF phải có **lớp chữ**. Bản scan chỉ là ảnh thì Claude không đọc được gì.
  Khi ấy phải chạy nhận dạng chữ (OCR) trước, ví dụ bằng Adobe Acrobat.
- Bài rất dài bị cắt bớt phần cuối; bản ghi sẽ có cờ `text_truncated` để cô
  biết mà kiểm kỹ.
- Mỗi lượt tải PDF lên là một lượt gọi API tính tiền vào tài khoản của cô.
- Mô hình mặc định là `claude-sonnet-5`. Muốn đổi thì sửa dòng `LLM_MODEL=`
  trong `backend\.env`.
- Máy chủ chỉ nghe trên chính máy cô (`127.0.0.1`), nên máy khác cùng mạng
  Wi-Fi không vào được.

## Đổi hoặc xoá mã khoá

Mở `backend\.env` bằng Notepad, sửa hay xoá dòng `LLM_API_KEY=`. Xoá hẳn thì
lần chạy sau tệp `.bat` sẽ hỏi lại. Nếu nghi mã bị lộ, **thu hồi** nó trên
console.anthropic.com rồi tạo mã mới.
