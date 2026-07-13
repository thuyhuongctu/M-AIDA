# AI_USE_DISCLOSURE: Khai báo sử dụng trí tuệ nhân tạo (M-AIDA v7.1.1)

Tài liệu này khai báo minh bạch vai trò của mô hình ngôn ngữ lớn (LLM) trong
quy trình của M-AIDA phiên bản 7.1.1, nhất quán với nguyên tắc COPE: công cụ
AI không thể chịu trách nhiệm học thuật và không có tư cách tác giả.

## 1. Vai trò của LLM trong pipeline

LLM chỉ thực hiện **trích xuất cơ học** các đại lượng thống kê từ văn bản của
các nghiên cứu **đã xuất bản** (bài báo khoa học dạng PDF):

- Nhận diện hệ số trọng tâm của quan hệ quốc tế hóa và hiệu quả hoạt động
  (không lấy hệ số tương tác hay biến kiểm soát).
- Đề xuất các giá trị N, r, t, df, beta, p, khoảng tin cậy kèm điểm tin cậy
  ba mức; bản ghi có điểm tin cậy dưới 0,70 bị gắn cờ rà soát bắt buộc.
- Việc quy đổi về hệ số r thực hiện bằng công thức tất định trong mã nguồn
  (Cohen, 1988; Peterson và Brown, 2005), không do LLM tự suy diễn.

LLM **không** được dùng để: tạo giá trị không tồn tại trong tài liệu nguồn;
suy đoán khi thiếu bằng chứng; gán các biến điều tiết ICRV, DPL, cDAI (các
biến này do người nghiên cứu chính gán thủ công từ bảng tra ngoài); quyết
định đưa vào hay loại ra nghiên cứu; khóa bản ghi; chạy mô hình thống kê;
hay viết nội dung diễn giải.

## 2. Kiến trúc đa nhà cung cấp và khóa của người dùng (BYOK)

- M-AIDA gọi mô hình qua **lớp adapter trung lập với nhà cung cấp**
  (`engines.py`), cấu hình bằng ba biến môi trường: `LLM_PROVIDER`,
  `LLM_API_KEY`, `LLM_MODEL`. Phần mềm không gắn với bất kỳ nhà cung cấp hay
  mô hình cụ thể nào.
- Người dùng tự cung cấp khóa API của mình (bring your own key). Khóa lưu
  trong tệp `.env` cục bộ, không đưa vào mã nguồn và không commit vào kho
  (tệp `.env` đã được git-ignore).
- Nhà cung cấp và mã định danh mô hình thực dùng cho từng đợt trích xuất được
  ghi vào `REPRODUCIBILITY_MANIFEST.json` tại thời điểm chạy.

## 3. Dữ liệu gửi đi và không gửi đi

**Gửi đến nhà cung cấp mô hình:** văn bản bóc tách từ PDF của các nghiên cứu
đã xuất bản (nội dung học thuật công khai) và câu lệnh trích xuất (prompt).

**Không gửi:** dữ liệu cá nhân của người dùng; khóa API của dịch vụ khác; các
bản thảo chưa công bố của luận án; giá trị đã xác minh hay ghi chú nội bộ của
người nghiên cứu chính; toàn bộ cơ sở dữ liệu nghiên cứu đã mã hóa.

Việc gửi văn bản đến nhà cung cấp bên ngoài chịu sự điều chỉnh của điều khoản
dịch vụ của nhà cung cấp đó; người dùng cần rà soát điều khoản này khi cấu
hình adapter.

## 4. Con người quyết định (Human-in-the-loop)

Mọi giá trị do LLM đề xuất phải qua chuỗi kiểm soát bắt buộc trước khi vào
phân tích:

1. Máy trích xuất và chấm điểm tin cậy.
2. Người nghiên cứu chính (PI) đối chiếu với tài liệu nguồn.
3. PI sửa hoặc ghi đè từng trường khi cần (`field_overrides`).
4. PI phê duyệt (`pi_approved`).
5. Khóa bất biến kèm dấu thời gian UTC (`pi_locked`, `locked_at`); bản ghi đã
   khóa không thể sửa.
6. Chỉ bản ghi đã khóa mới được xuất vào bộ dữ liệu phân tích.

Trách nhiệm khoa học đối với mọi giá trị trong bộ dữ liệu cuối thuộc về các
tác giả con người.

## 5. Dấu vết kiểm toán (Audit trail)

Mỗi bản ghi lưu: giá trị máy đề xuất, điểm tin cậy, cờ rà soát bắt buộc, các
ghi đè của PI, ghi chú xác minh (`pi_notes`, bao gồm nguồn trang hoặc bảng và
lý do điều chỉnh theo quy ước ghi chép), trạng thái phê duyệt và dấu thời
gian khóa. Chi tiết trường dữ liệu: xem `DATA_DICTIONARY.md`.
