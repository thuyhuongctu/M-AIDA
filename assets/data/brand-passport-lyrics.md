# Brand Passport (Vietnam to the World)

**Tác giả lời:** Đỗ Thùy Hương
**Ngôn ngữ:** tiếng Anh, xen tiếng Pháp
**Bản ghi trong kho nhạc:**

| Bản | Tệp | Thời lượng |
|---|---|--:|
| Bản gốc | `assets/maida_song_brand_passport.mp3` | 5:19 |
| Bản phối lại (remix) | `assets/maida_song_brand_passport_remix.mp3` | 5:33 |

Bài hát thuộc tuyến nội dung "Vietnam to the World", đi cùng chủ đề quốc tế hóa
doanh nghiệp của chương trình nghiên cứu: mỗi thị trường để lại một con dấu, mỗi
lựa chọn mở ra một lối đi, và bản lĩnh nằm ở chỗ học được gì sau mỗi lần vấp chứ
không phải ở chỗ chưa từng vấp.

## Cấu trúc

Intro (giọng hát nhẹ, đàn tranh và sáo trúc) · Verse 1 · French Bridge ·
Verse 2 · Pre-Final Chorus · Final Chorus (chuyển tông, hợp xướng đầy) ·
Final Drop và Chant · Outro (tiếng nước xa dần).

## Trạng thái phần lời trên trang

`songs.html` chạy khối lời đồng bộ (`.lblk`) cho bản được đánh dấu `lyr:true`
trong mảng `TRACKS`; điều kiện kích hoạt trong `timeupdate` đọc cờ đó. Hiện chỉ
tác phẩm chính mang cờ. Muốn hiện lời cho bài này thì phải chuyển phần lời sang
cấu trúc theo từng bài rồi chọn khối lời theo bài đang phát, chứ không chỉ thêm
khối mới vào trang. Đây là việc UI riêng, chưa làm; hai bản ghi đã phát được
bình thường trong danh sách.

> **Đính chính 22/08/2026.** Đoạn trên trước đây viết rằng điều kiện kích hoạt
> "gắn cứng với tên tệp `maida_song_official`". Câu đó mô tả phiên bản mã cũ
> (`TRACKS[cur].f.indexOf('maida_song_official')>=0`) và **sai ngay từ lúc tệp
> này được tạo**: commit `2c19f90` ngày 02/08/2026 vừa thêm tài liệu này vừa đổi
> mã sang đọc cờ `lyr`, nên câu mô tả đã lỗi thời trong chính commit sinh ra nó.
> `la-recherche-lyrics.md`, tệp tài liệu bài hát còn lại, mô tả đúng cơ chế cờ
> `lyr` từ đầu; chỉ tệp này lệch.

## Ghi chú bản quyền

Phần lời và hai bản ghi thuộc quyền tác giả của Đỗ Thùy Hương, phát hành cùng dự
án M-AIDA. Xem `LICENSE` và `COMMERCIAL-LICENSE.md` cho điều kiện sử dụng lại.
