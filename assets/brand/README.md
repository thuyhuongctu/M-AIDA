# M-AIDA — Bộ tệp nhận diện

Hướng A: hình thoi gộp chia đôi. Nửa trái rỗng viền mực là bản ghi máy đề xuất,
nửa phải đặc hổ phách là bản ghi người đã khóa, trục ngang là đường không hiệu
ứng của biểu đồ rừng.

Chữ trong mọi tệp SVG đã được chuyển thành đường vẽ, nên logo hiển thị đúng kể
cả khi máy người xem không có phông Source Serif 4 hay JetBrains Mono.

## Tệp

| Tệp | Dùng ở đâu |
|---|---|
| `maida-mark.svg` | Dấu hiệu đầy đủ, có trục. Dùng từ 24px trở lên. |
| `maida-mark-small.svg` | Bỏ trục. Dùng cho 16–23px. |
| `maida-mark-mono.svg` | Một màu, cho in đen trắng và phụ lục luận án. |
| `maida-lockup-horizontal.svg` | Đầu trang web, chân trang, chữ ký email. |
| `maida-lockup-stacked.svg` | Bìa, slide, chỗ hẹp chiều ngang. |
| `maida-lockup-academic.svg` | Bài báo, poster hội thảo, trang bảo vệ. |
| `maida-lockup-dark.svg` | Nền console, ảnh chụp màn hình tối. |
| `favicon.svg` · `/favicon.ico` | Trình duyệt. Bản rút gọn, chỉ khối đặc. |
| `/apple-touch-icon.png` | 180×180, màn hình chính iOS. |
| `/icons/icon-maskable-512.png` | 512×512, Android. Nội dung nằm trong 60% giữa. |
| `/og-image.png` | 1200×630, ảnh chia sẻ mạng xã hội. |

## Nhúng vào trang

```html
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon.ico" sizes="48x48">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta property="og:image" content="https://thuyhuongctu.github.io/M-AIDA/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
```

## Màu

| Vai trò | Mã |
|---|---|
| Mực | `#1a1714` |
| Hổ phách — đã khóa và đã gộp | `#c0862a` |
| Trục, đường kẻ mảnh | `#c4b8a1` |
| Nền giấy | `#f6f1e7` |
| Nền console | `#171a19` |
| Mực trên console | `#e8e4d9` |

## Quy tắc

- Khoảng trống bắt buộc quanh dấu hiệu bằng nửa chiều cao hình thoi. Khi đặt
  cạnh logo Đại học Cần Thơ thì gấp rưỡi khoảng đó, và cân theo chiều cao chữ
  chứ không theo chiều cao khung.
- Không tô hổ phách cả hai nửa. Không xoay hình thoi. Không đổi màu hổ phách
  sang màu khác.
- Không đặt logo lên ảnh chụp; chỉ đặt trên nền giấy hoặc nền console.
- Không dùng logo thay cho hình thoi gộp trong biểu đồ rừng thật — dữ liệu và
  nhận diện phải tách bạch.
- Bản dưới 16px là tệp riêng, không phải bản thu nhỏ tự động.

## Giao diện

Biến gốc và thành phần chuẩn nằm ở `css/tokens.css` và `css/components.css`
(nạp tokens trước, components sau). Trang đối chiếu sống: `/styleguide.html`;
bản độc lập không cần mạng nội bộ: `/styleguide-standalone.html`.
