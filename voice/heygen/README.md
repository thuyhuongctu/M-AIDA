# Sinh toàn bộ âm thanh M-AIDA bằng HeyGen / Generating all M-AIDA audio with HeyGen

Thư mục này chứa quy trình tái tạo **toàn bộ** âm thanh của trang M-AIDA bằng
HeyGen API — giọng thuyết minh tour, ghi chú bản đồ atlas (Anh + Việt), và
phần lời cho ca khúc chủ đề. Mọi tệp đều được ghi đồng thời vào bản gốc và
bản mirror `docs/` (GitHub Pages) để hai nơi luôn khớp nhau.

This folder regenerates **every** audio asset on the M-AIDA site through the
HeyGen API: the guided-tour narration, the atlas country notes (EN + VI), and
the theme-song vocal. Each file is written to both the root site and the
`docs/` GitHub Pages mirror in one run.

## Danh sách âm thanh / Audio inventory

| Nhóm | Tệp | Ngôn ngữ |
|------|-----|----------|
| Tour thuyết minh | `voice/stop1-6.mp3` | English |
| Tour thuyết minh | `voice/vi/stop1-6.mp3` | Tiếng Việt |
| Ghi chú atlas | `voice/atlas/{china,india,vietnam,poland,turkey,generic}.mp3` | English |
| Ghi chú atlas | `voice/atlas/vi_{china,india,vietnam,poland,turkey,generic}.mp3` | Tiếng Việt — trước đây **chưa tồn tại** dù `index.html` đã tham chiếu; manifest này bổ sung chúng |
| Bài hát | `assets/heygen/maida_song_vocal.mp3` (giọng đọc lời «Que les preuves décident») | Tiếng Việt |

Kịch bản (script) của từng tệp nằm trong `manifest.json` và được lấy đúng
nguyên văn từ mảng `TOUR` cùng hàm `noteText` trong `index.html`, nên giọng
đọc luôn khớp với phụ đề hiển thị trên trang.

## Chuẩn bị / Setup

Script hỗ trợ hai "engine":

- **`cli` (khuyến nghị)** — HeyGen CLI v3 chính thức, sinh audio TTS trực tiếp
  bằng `heygen voice speech create`. Đây là đường đi được gói skill chính thức
  của HeyGen ([github.com/heygen-com/skills](https://github.com/heygen-com/skills))
  khuyến nghị; các endpoint REST v1/v2 đã bị HeyGen đánh dấu deprecated.
- **`api` (dự phòng)** — REST v2 cũ: render video avatar tối giản rồi tách
  tiếng. Chỉ dùng khi không cài được CLI.

1. Cài CLI và cấu hình key:

   ```bash
   curl -fsSL https://static.heygen.ai/cli/install.sh | bash
   export HEYGEN_API_KEY=...   # tuyệt đối không ghi key vào tệp / never commit the key
   # hoặc đăng nhập OAuth: heygen auth login
   # cần ffmpeg trên PATH để chuẩn hóa âm lượng và xuất MP3
   # (engine api cần thêm: pip install requests)
   ```

2. **Giọng "Hương AI"**: để giữ đúng persona của trang (giọng nhân bản từ
   chính giọng thu của tác giả, có sự đồng ý của tác giả), hãy clone giọng
   trong HeyGen (Voice → Clone voice) từ bản thu của Đỗ Thùy Hương, lấy
   `voice_id` rồi điền vào `manifest.json` mục `voices.en.voice_id` và
   `voices.vi.voice_id`. Nếu để trống, script tự chọn giọng Anh/Việt đầu tiên
   trong tài khoản (chỉ nên dùng để thử).

   ```bash
   python voice/heygen/generate.py --list-voices
   ```

## Chạy / Run

```bash
# Xem trước, không gọi API
python voice/heygen/generate.py --dry-run

# Sinh toàn bộ (tour + atlas + bài hát)
python voice/heygen/generate.py

# Chỉ một nhóm hoặc một ngôn ngữ
python voice/heygen/generate.py --group tour --lang vi
python voice/heygen/generate.py --group atlas

# Chỉ một vài tệp
python voice/heygen/generate.py --only tour_en_stop1,atlas_vi_vietnam

# Ép chọn engine (mặc định auto: có CLI thì dùng CLI)
python voice/heygen/generate.py --engine cli
python voice/heygen/generate.py --engine api   # REST v2 cũ, deprecated
```

Với engine `cli`, mỗi câu được tổng hợp trực tiếp thành audio; với engine
`api`, script render một video tối giản rồi tách tiếng. Cả hai trường hợp
audio đều được chuẩn hóa âm lượng (EBU R128, I=-16 LUFS) và xuất MP3
44,1 kHz bằng ffmpeg.

Nếu dùng Claude Code, có thể cài thêm bộ skill chính thức của HeyGen
(`heygen-avatar`, `heygen-video`, `heygen-translate`) để tạo avatar
"Hương AI", clone giọng và làm video thuyết trình:

```bash
git clone --single-branch --depth 1 https://github.com/heygen-com/skills.git ~/.claude/skills/heygen-skills
```

## Về bài hát / About the song

Lời «Que les preuves décident» của Đỗ Thùy Hương (17/07/2026) được bảo lưu
mọi quyền và **không** lưu trong repo. Muốn sinh phần giọng cho bài hát:

1. Dán lời vào `voice/heygen/song_lyrics.txt` (tệp này nằm trong `.gitignore`).
2. Chạy `python voice/heygen/generate.py --group song`.

Lưu ý: HeyGen tổng hợp **giọng nói**, không hát. Kết quả là bản đọc lời
(spoken-word) xuất ra `assets/heygen/maida_song_vocal.mp3`. Bản phối nhạc
`assets/maida_song.mp3` vẫn do công cụ sinh nhạc tạo ra và script không bao
giờ ghi đè tệp này trừ khi truyền `--overwrite-song`.

## Sau khi sinh xong / After generating

- Nghe thử từng tệp; kiểm tra số liệu đọc đúng (ví dụ "r = 0,074").
- Commit các tệp mp3 mới ở cả `voice/`, `docs/voice/` và `assets/heygen/`.
- Không cần sửa `index.html`: đường dẫn tệp giữ nguyên nên trang tự dùng
  giọng mới.
