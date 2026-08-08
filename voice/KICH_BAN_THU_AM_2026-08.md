# Kịch bản thu âm — lời thoại tour sau khi rút con số

Ngày kịch bản: 04/08/2026 · Nguồn: mảng `TOUR` trong `index.html` (trích tự động, không chép tay — `docs/index.html` dùng cùng lời thoại).

**Cần thu: 10 tệp** (5 chặng × EN/VI). **Chặng 3 không đổi chữ nào — hai tệp `stop3.mp3` và `vi/stop3.mp3` giữ nguyên, đừng thu lại.**

Định dạng như bộ cũ: MP3, giọng nhân vật đã nhân bản, đặt đúng tên tệp vào `voice/` (bản tiếng Anh) và `voice/vi/` (bản tiếng Việt). Quy tắc đang bảo vệ lớp này: nhân vật dẫn dắt và giải thích quy trình, KHÔNG đọc con số — con số nằm trên màn hình. Sau lần thu này, dữ liệu đổi bao nhiêu cũng không phải thu lại.


---

## Chặng 1 (overview)

### Tệp `voice/stop1.mp3` — tiếng Anh

> Bonjour à tous! Je m'appelle Hương. Welcome to M-AIDA, the Meta-Analysis Intelligent Data Assistant, the research software I built for my doctoral dissertation at Can Tho University under the supervision of Associate Professor Doctor Phan Anh Tu. It read hundreds of studies spanning nearly five decades and prepared hundreds of verified effect-size records on internationalization and firm performance across dozens of economies - the exact counts are on screen, straight from the locked dataset.

### Tệp `voice/vi/stop1.mp3` — tiếng Việt

> Bonjour à tous! Je m'appelle Hương. Chào mừng đến với M-AIDA - Trợ lý Dữ liệu Thông minh cho Phân tích Tổng hợp, phần mềm tôi xây dựng cho luận án tiến sĩ tại Trường Đại học Cần Thơ, dưới sự hướng dẫn của PGS.TS. Phan Anh Tú. Hệ thống đã đọc hàng trăm nghiên cứu trải gần năm thập kỷ và chuẩn bị hàng trăm bản ghi mức độ ảnh hưởng đã kiểm chứng về quốc tế hóa và hiệu quả doanh nghiệp trên hàng chục nền kinh tế - con số chính xác nằm trên màn hình, lấy thẳng từ tập dữ liệu đã khóa.


---

## Chặng 2 (method)

### Tệp `voice/stop2.mp3` — tiếng Anh

> The workflow has three gates: extract, verify, lock. A large language model reads each full-text PDF and proposes the statistics - sample size, correlation, t statistic, standardized beta - each with a confidence score. Anything below the confidence threshold is flagged for mandatory human review. I verify every field against the source page myself; approved records are locked immutably with a timestamp, so no number can be quietly changed afterwards. Every conversion follows published formulas only: t to r following Cohen, beta to r following Peterson and Brown - the full citations are on screen.

### Tệp `voice/vi/stop2.mp3` — tiếng Việt

> Quy trình có ba cửa kiểm soát: trích xuất, kiểm chứng, khóa. Mô hình ngôn ngữ lớn đọc toàn văn từng PDF và đề xuất số liệu - cỡ mẫu, hệ số tương quan, thống kê t, beta chuẩn hóa - kèm điểm tin cậy. Dưới ngưỡng tin cậy bị gắn cờ buộc con người rà soát. Tôi tự kiểm từng trường so với trang nguồn; bản ghi được duyệt sẽ khóa bất biến kèm dấu thời gian, không ai sửa lén được. Mọi quy đổi chỉ dùng công thức đã công bố: t sang r theo Cohen, beta sang r theo Peterson và Brown - trích dẫn đầy đủ nằm trên màn hình.


---

## Chặng 3 (landscape) — KHÔNG THU LẠI

`voice/stop3.mp3` và `voice/vi/stop3.mp3` giữ nguyên (lời thoại không đổi chữ nào).


---

## Chặng 4 (forest)

### Tệp `voice/stop4.mp3` — tiếng Anh

> Here is the output. Each square is one study's effect size; the amber diamond is the pooled estimate - positive but small, with substantial heterogeneity across studies. Correcting for publication bias pulls it lower still, and the dissertation reports those corrections as part of the finding, not a footnote. The numbers themselves live on the chart, read straight from the locked dataset.

### Tệp `voice/vi/stop4.mp3` — tiếng Việt

> Đây là đầu ra. Mỗi ô vuông là mức độ ảnh hưởng của một nghiên cứu; hình thoi hổ phách là ước lượng gộp - dương nhưng nhỏ, với dị biệt đáng kể giữa các nghiên cứu. Hiệu chỉnh thiên lệch xuất bản còn kéo giá trị xuống thấp hơn, và luận án báo cáo các hiệu chỉnh này như một phần của phát hiện, không phải chú thích. Bản thân con số nằm trên biểu đồ, đọc thẳng từ tập dữ liệu đã khóa.


---

## Chặng 5 (atlas)

### Tệp `voice/stop5.mp3` — tiếng Anh

> The atlas maps dozens of economies, plus the cross-border studies that are counted but not pinned to a single country. Colour shows each country's mean effect; click any country to see its numbers on screen and hear its story.

### Tệp `voice/vi/stop5.mp3` — tiếng Việt

> Bản đồ atlas thể hiện hàng chục nền kinh tế, cùng các nghiên cứu xuyên biên giới được đếm nhưng không gắn vào một quốc gia. Màu sắc thể hiện hiệu ứng trung bình từng nước; bấm vào một quốc gia để xem con số trên màn hình và nghe câu chuyện của nước đó.


---

## Chặng 6 (tool)

### Tệp `voice/stop6.mp3` — tiếng Anh

> And this is the demo you can try yourself, right in the browser. Start from one of the three sample papers - one reports a correlation, one a t statistic, one a standardized beta - and walk them through the same gates as the real system: convert, verify, lock, export. Reading real PDFs needs the backend with your own API key: bring your own key, your data stays yours. When you finish, visit the songs page - this project even has its own album, The M-AIDA Archive, with lyrics I wrote myself. Merci beaucoup, et que les preuves décident!

### Tệp `voice/vi/stop6.mp3` — tiếng Việt

> Và đây là bản demo cô/bạn có thể tự thử ngay trong trình duyệt. Hãy bắt đầu từ một trong ba bài mẫu - một bài báo cáo hệ số tương quan, một bài thống kê t, một bài beta chuẩn hóa - rồi đưa chúng qua đúng các cửa kiểm soát của hệ thật: quy đổi, kiểm chứng, khóa, xuất. Đọc PDF thật cần backend với API key riêng: khóa của bạn, dữ liệu vẫn là của bạn. Xem xong, mời ghé trang bài hát - dự án này có hẳn album riêng, The M-AIDA Archive, với phần lời do chính tôi viết. Merci beaucoup, et que les preuves décident!


---

## Kết quả kiểm 10 tệp atlas (05/08/2026) — 8 giữ, 2 thu lại

Kịch bản của từng tệp truy từ `STORY` trong mã và commit lắp tệp (đợt 02/08 có
bước nhận dạng-đối chiếu nội dung từng tệp). Bốn cặp quốc gia
(`turkey/poland/india/china` + bản `vi_`) chỉ chứa năm xuất bản trong trích
dẫn công trình của nhóm tác giả — bất biến, KHÔNG thu lại. Riêng câu chung
nói "một trong 35 nền kinh tế" — con số dữ liệu có thể đổi sau v8:

### Tệp `voice/atlas/generic.mp3` — tiếng Anh (THU LẠI)

> One of the economies in this atlas - its numbers are on screen, read straight from the locked dataset.

### Tệp `voice/atlas/vi_generic.mp3` — tiếng Việt (THU LẠI)

> Một trong các nền kinh tế của bản đồ này - con số nằm trên màn hình, đọc thẳng từ tập dữ liệu đã khóa.

## Danh sách kiểm sau khi thu

- [x] 10 tệp tour mới đặt đúng tên, đúng thư mục (`voice/`, `voice/vi/`) — xong 04-05/08.
- [x] 2 tệp atlas generic mới (EN + VI) — xong 05/08.
- [ ] Mở tour, TTS dự phòng không bật (tức tệp mp3 được tìm thấy).
- [ ] Nghe lướt: không tệp nào đọc một chữ số dữ liệu.
- [x] `stop3` hai bản vẫn là tệp cũ (không thu thừa).
