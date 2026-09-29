# Kịch bản thu âm: lời thoại tour tiếng Việt theo bảng thuật ngữ

Ngày kịch bản: 25/09/2026 · **Đã thu xong 26/09/2026:** cả 6 tệp tiếng Việt và 6 tệp tiếng Anh · Nguồn: mảng `TOUR` trong `index.html` (trích tự động bằng Node, không chép tay).

**Cần thu: 6 tệp**, tất cả ở `voice/vi/` (`stop1.mp3` đến `stop6.mp3`). **Không thu lại bản tiếng Anh** (`voice/stop*.mp3`) và **không thu lại các tệp bản đồ** (`voice/atlas/`): lời của chúng không đổi.

Vì sao thu lại: lời thoại tiếng Việt cũ còn thuật ngữ có từ trước khi có `THUAT_NGU_VA_QUY_TAC_TIENG_VIET.md` («bản ghi mức độ ảnh hưởng», «thiên lệch xuất bản», «cửa kiểm soát»...). Chữ trên trang đã sửa theo bảng thuật ngữ; **cho tới khi thu xong, giọng đọc tiếng Việt sẽ lệch với phụ đề** ở cả sáu chặng.

Quy tắc giữ nguyên như lần trước: MP3, giọng nhân vật đã nhân bản, **không đọc con số dữ liệu**, con số nằm trên màn hình. Các câu tiếng Pháp (lời chào mở đầu, lời chào cuối) đọc bằng giọng Pháp như bản cũ.

---

## Chặng 1 (overview: Giới thiệu)

### Tệp `voice/vi/stop1.mp3`

> Bonjour à tous! Je m'appelle Hương. Chào mừng bạn đến với M-AIDA, Trợ lý Dữ liệu Thông minh cho Phân tích Tổng hợp. Tôi xây dựng phần mềm này cho luận án tiến sĩ tại Trường Đại học Cần Thơ, dưới sự hướng dẫn của PGS.TS. Phan Anh Tú. M-AIDA đã đọc hàng trăm nghiên cứu trải gần năm thập kỷ, và chuẩn bị hàng trăm bản ghi cỡ ảnh hưởng đã kiểm chứng về quốc tế hóa và hiệu quả doanh nghiệp ở hàng chục nền kinh tế. Con số chính xác nằm trên màn hình, lấy thẳng từ bộ dữ liệu đã khóa.

---

## Chặng 2 (method: Phương pháp)

### Tệp `voice/vi/stop2.mp3`

> Quy trình có ba cổng: trích xuất, kiểm chứng, khóa. Mô hình ngôn ngữ lớn đọc toàn văn từng PDF và đề xuất số liệu: cỡ mẫu, hệ số tương quan, thống kê t, beta chuẩn hóa, kèm điểm tin cậy. Bản ghi nào dưới ngưỡng tin cậy đều bị gắn cờ, bắt buộc con người rà soát. Tôi tự kiểm từng trường, đối chiếu với trang nguồn. Bản ghi đã duyệt thì khóa bất biến kèm dấu thời gian, nên không ai sửa lén được con số nào. Mọi phép quy đổi chỉ dùng công thức đã công bố: t sang r theo Cohen, beta sang r theo Peterson và Brown. Trích dẫn đầy đủ nằm trên màn hình.

---

## Chặng 3 (landscape: Định vị)

### Tệp `voice/vi/stop3.mp3`

> M-AIDA không thay thế các công cụ sàng lọc như Rayyan hay ASReview, cũng không chạy thống kê như metafor trong R. Nó lo khâu hẹp nhưng tốn công nhất nằm giữa hai việc đó: trích xuất, quy đổi và quản lý cỡ ảnh hưởng. Bản ghi nào cũng truy ngược được về trang và bảng gốc.

---

## Chặng 4 (forest: Biểu đồ rừng)

### Tệp `voice/vi/stop4.mp3`

> Đây là đầu ra. Mỗi ô vuông là cỡ ảnh hưởng của một nghiên cứu; hình thoi màu hổ phách là ước lượng gộp: dương nhưng nhỏ, và tính dị biệt giữa các nghiên cứu khá lớn. Hiệu chỉnh thiên lệch công bố còn kéo giá trị xuống thấp hơn nữa. Luận án coi các hiệu chỉnh này là một phần của kết quả, không phải chú thích bên lề. Còn các con số thì nằm trên biểu đồ, đọc thẳng từ bộ dữ liệu đã khóa.

---

## Chặng 5 (atlas: Bản đồ nghiên cứu)

### Tệp `voice/vi/stop5.mp3`

> Bản đồ nghiên cứu thể hiện hàng chục nền kinh tế, cùng các nghiên cứu xuyên biên giới có tính vào tổng số nhưng không gắn với riêng quốc gia nào. Màu sắc cho biết ảnh hưởng trung bình của từng nước. Bấm vào một quốc gia để xem số liệu trên màn hình và nghe câu chuyện của nước đó.

---

## Chặng 6 (tool: Bản demo)

### Tệp `voice/vi/stop6.mp3`

> Và đây là bản demo bạn có thể tự thử ngay trong trình duyệt. Hãy bắt đầu từ một trong ba bài mẫu: một bài báo cáo hệ số tương quan, một bài báo cáo thống kê t, một bài báo cáo beta chuẩn hóa. Rồi đưa chúng qua đúng các cổng như hệ thống thật: quy đổi, kiểm chứng, khóa, xuất dữ liệu. Muốn đọc PDF thật thì cần backend với khóa API của riêng bạn: khóa của bạn, dữ liệu vẫn là của bạn. Xem xong, mời bạn ghé trang bài hát. Dự án này có hẳn một album riêng, The M-AIDA Archive, với phần lời do chính tôi viết. Merci beaucoup, et que les preuves décident!

---

## Kiểm trước khi gửi

- [ ] Đủ 6 tệp, đúng tên, đặt trong `voice/vi/`, ghi đè tệp cũ.
- [ ] Không câu nào đọc số liệu.
- [ ] Chặng 2: «t sang r theo Cohen», «beta sang r theo Peterson và Brown».
- [ ] Mở trang ở tiếng Việt, bấm tour, nghe hết sáu chặng xem giọng có khớp phụ đề không.
