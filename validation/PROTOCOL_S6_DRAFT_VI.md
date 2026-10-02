# Bản nháp sửa §6 VALIDATION_PROTOCOL (chờ PI quyết)

**Trạng thái: NHÁP.** Tệp này không thay `VALIDATION_PROTOCOL.md`. §6 hiện
hành vẫn có hiệu lực cho đến khi nghiên cứu sinh duyệt và chép phần đã chọn
vào protocol bằng một commit riêng, **trước** khi khóa sampling frame và trước
mọi lượt chạy thật. Mọi quyết định dưới đây phải xong trước khi xem bất kỳ
đề xuất máy nào trên mẫu kiểm định.

## A. Bốn điểm cần quyết

### A1. Phiên bản đóng băng

§6 hiện ghi 7.1.1. Hai sự kiện kiểm tra được trong kho mã:

- System prompt của 7.1.1 khác 7.2.0 trở đi (băm SHA-256 của chuỗi prompt:
  7.1.1 `899db2dd38907fbf`, 7.2.0 đến 8.0.0 `5b04f150780dcc79`). Kết quả
  benchmark chạy bằng 7.1.1 vì vậy không mô tả công cụ đang phát hành, và
  ngược lại.
- Kịch bản chạy hàng loạt `validation/run_benchmark.py`, temperature cấu hình
  được và dấu vân tay prompt chỉ có từ 8.0.0. Muốn chạy 7.1.1 hay 7.2.3 phải
  chuyển ngược các phần này về nhánh cũ.

Phương án:

| | Đóng băng | Hệ quả |
|---|---|---|
| **(a) khuyến nghị** | Một commit có tag của dòng 8.0 (ví dụ `v8.0.0-val`) | Prompt trùng 7.2.x (`sha256:fb368e1cb9123eef`), có đủ công cụ; kết quả mô tả đúng bản đang dùng |
| (b) | 7.2.3 + chuyển ngược kịch bản chạy | Thêm việc, cùng prompt với (a) |
| (c) | 7.1.1 | Phải chuyển ngược nhiều; kết quả chỉ nói về prompt cũ |

Dù chọn phương án nào, 7.1.1 vẫn là **phiên bản đăng ký bản quyền**; ghi tách
bạch hai vai trò: "phiên bản đăng ký: 7.1.1; phiên bản kiểm định: …".

### A2. Một đề xuất mỗi bài và đơn vị đo

M-AIDA (mọi phiên bản đến 8.0) trả **một** hệ số cho mỗi PDF. Protocol lấy
**candidate effect** làm đơn vị và §2 yêu cầu có bài nhiều hệ số. Trong 40 bài
PRIMARY của khung hiện tại, cơ sở dữ liệu P6 ghi 54 hệ số (27 bài một hệ số,
12 bài hai, 1 bài ba). Nếu cả 54 đều in-scope trong chuẩn vàng thì recall tối
đa là 40/54 = 0,74 và F1 tối đa khoảng 0,85 ngay cả khi precision bằng 1, tức
ngưỡng F1 ≥ 0,90 ở §5 không thể đạt về mặt cấu trúc.

Phương án (chọn trước khi chạy; không đổi sau khi xem kết quả):

- **(i)** Giữ nguyên đơn vị candidate effect và ngưỡng; báo cáo kết quả dưới
  ngưỡng như một giới hạn đã biết của thiết kế một đề xuất mỗi bài.
- **(ii)** Chỉ số chính đo ở cấp **bài** với hệ số trọng tâm do người mã hóa
  xác định trước (một case in-scope mỗi bài); recall cấp candidate effect báo
  cáo là chỉ số phụ, không so ngưỡng.
- **(iii)** Phát triển M-AIDA đề xuất nhiều hệ số mỗi bài **trước** khi đóng
  băng (thay đổi công cụ; cần chạy lại toàn bộ kiểm thử).

Công cụ hiện tại chạy được với (i) và (ii) mà không sửa mã; (ii) chỉ cần quy
ước mã hóa `in_scope` theo hệ số trọng tâm.

### A3. Ai liệt kê candidate effect

`analyze_validation.py` so hai người mã hóa theo từng `case_id`, nên danh sách
candidate effect phải chung và có trước khi mã hóa (§7 bước 1 cũng yêu cầu
tạo `case_id` trước khi chạy M-AIDA). Sổ tay §2 lại viết "coder ghi cả…", tức
mỗi người tự liệt kê. Đề xuất: một người liệt kê **chỉ vị trí** (trang, bảng,
mô hình, dòng/cột), không ghi giá trị, không đánh dấu hệ số trọng tâm, trong
`case_enumeration.xlsx`; người mã hóa ghi vào `notes` hệ số bị bỏ sót, người
phân xử bổ sung **trước** khi chạy M-AIDA. Nếu người liệt kê là PI (cũng là
người mã hóa 1), ghi rõ điều này trong báo cáo.

### A4. So sánh thời gian

Người mã hóa 1 là PI, và PI cũng là người kiểm chứng đề xuất máy. Khi kiểm
chứng, PI đã biết đáp án của chính mình trên cùng bài, nên thời gian kiểm chứng
sẽ bị ước lượng thấp và mức tiết kiệm thời gian bị phóng đại. Phương án:

- khoảng nghỉ tối thiểu (ví dụ 4 tuần) giữa mã hóa thủ công và kiểm chứng, vẫn
  ghi nhận là hạn chế; hoặc
- chia ngẫu nhiên các bài: một nửa PI mã hóa thủ công, một nửa PI kiểm chứng
  đề xuất máy mà chưa mã hóa (người mã hóa 2 vẫn mã hóa toàn bộ cho chuẩn
  vàng); thời gian so sánh giữa hai nửa; hoặc
- báo cáo thời gian là chỉ số mô tả, không kết luận hiệu quả.

Với bài máy từ chối (thiếu bằng chứng), thời gian kiểm chứng là thời gian PI
thực sự bỏ ra trong quy trình có M-AIDA, kể cả mã hóa tay thay thế.

## B. Văn bản đề xuất cho §6 (giả định chọn A1-a)

> ## 6. Điều kiện tái lập
>
> - **Phần mềm kiểm định:** M-AIDA commit `<SHA>` (tag `<tag>`), dòng 8.0.
>   Phiên bản đăng ký bản quyền là 7.1.1; hai vai trò được ghi tách bạch.
> - **Mô hình:** `LLM_PROVIDER=anthropic`; `LLM_MODEL` ghi đúng một mã mô hình
>   cố định (kiểm tra trong tài liệu nhà cung cấp mã đó là bản cố định, không
>   phải bí danh tự cập nhật); `LLM_TEMPERATURE=0`. Temperature 0 giảm nhưng
>   không bảo đảm loại bỏ biến thiên giữa các lần gọi; vì vậy kết quả là **một
>   lượt chạy duy nhất**, không chạy lại để chọn lượt tốt hơn.
> - **Prompt:** dấu vân tay `sha256:fb368e1cb9123eef` (system prompt, mẫu tin
>   nhắn, giới hạn 40.000 ký tự văn bản PDF, 1.024 token đầu ra); tối đa 80
>   trang mỗi PDF; siêu dữ liệu gửi kèm chỉ gồm nhãn tác giả và năm của khung
>   mẫu. Thử lại tối đa 2 lần, chỉ khi lỗi phía nhà cung cấp.
> - **Chạy:** `validation/run_benchmark.py --lock <tệp khóa>`; kịch bản từ chối
>   khung chưa khóa, temperature chưa đóng băng, `LLM_MODEL` trống, cây mã có
>   thay đổi chưa commit, và không ghi đè thư mục chạy. `run_manifest.json`
>   của đợt chạy là REPRODUCIBILITY_MANIFEST: phiên bản, commit, mô hình,
>   temperature, dấu vân tay prompt, giới hạn, checksum tệp khóa và từng PDF,
>   ngày chạy, người chạy, số token.
> - **Ghép đề xuất (ghi trước):** mỗi đề xuất được ghép với case của chuẩn vàng
>   cùng vị trí với câu trích bằng chứng của nó. Đề xuất ứng với hệ số có thật
>   nhưng thiếu trong danh sách ghi `NOT_IN_FRAME`; đề xuất có giá trị không có
>   trong bài ghi `HALLUCINATED`. Cả hai được người phân xử thêm vào chuẩn vàng
>   với ghi chú `ADDED_AFTER_RUN` và báo cáo số lượng; không đề xuất nào bị bỏ.
> - **Phân tích:** `validation/build_predictions.py` rồi
>   `validation/analyze_validation.py` (chỉ dùng thư viện chuẩn), dung sai r
>   ±0,005.
> - **Lưu trữ:** thư mục chạy nguyên vẹn, chuẩn vàng đã khóa, sổ của hai người
>   mã hóa, `predictions.csv`, JSON chỉ số, báo cáo Markdown, checksum SHA-256
>   của từng tệp. Unit test của các script không phải kết quả kiểm định.

Nếu chọn A1-a, tiêu đề protocol đổi "(M-AIDA v7.1.1)" thành phiên bản kiểm
định, và §8 thêm thư mục chạy vào danh sách đầu ra.
