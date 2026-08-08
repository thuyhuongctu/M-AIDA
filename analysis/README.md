# M-AIDA · Bước 1 — Sửa ba công thức A1–A3

Gói mã thay thế cho tầng chuyển đổi cỡ ảnh hưởng của M-AIDA v7.1.1.
Bản backend (`backend/extractor.py`) đã được đồng bộ theo đúng ngữ nghĩa
của gói này; module ở đây là bản chuẩn độc lập dùng cho việc mã lại
dữ liệu và cho pipeline R.

| Tệp | Nội dung |
|---|---|
| `effect_size.py` | Module Python đã sửa, kèm bộ mã lại CSV (`recode_csv`) |
| `test_effect_size.py` | 20 kiểm thử đơn vị, mọi giá trị kỳ vọng đều tính tay |
| `effect_size.R` | Bản R tương đương, tự kiểm tra khi chạy `Rscript analysis/effect_size.R`; phần cuối là khung quy trình metafor cho bước 3–7 (ba cấp/hai cấp, phương sai vững theo cụm, khoảng dự báo, PET-PEESE, giả thuyết chữ S) |
| `mau_cu.csv` · `mau_moi.csv` | Bộ dữ liệu mẫu trước và sau khi mã lại |
| `migrate_v8.py` | Bước 2: di trú lược đồ v7.1.1 → v8.0.0-draft, sinh bảng thu hồi thống kê nguồn cho 47 bản ghi `is_estimated = 1`, và hoàn tất khi có `--recovered` |

## Ba lỗi được sửa

**A1 — công thức Peterson & Brown thiếu số hạng λ.**
Bản cũ: `r = .98·β`. Đúng: `r = .98·β + .05·λ` với λ = 1 khi β ≥ 0 và
λ = 0 khi β < 0. Phép quy đổi chỉ hợp lệ trong khoảng β từ −0,50 đến 0,50;
ngoài khoảng đó bản ghi bị **loại trừ**, không phải chỉ gắn cờ.
Điểm quan trọng nhất: vì λ chỉ cộng cho β không âm, việc bỏ quên nó gây
**lệch một chiều** — chỉ hạ thấp các hiệu ứng dương. Sai số không tự triệt
tiêu khi lấy trung bình.

**A2 — bậc tự do.**
Bản cũ: `df = n − 2`. Đúng cho thống kê t lấy từ hồi quy bội:
`df = n − p − 1`. Thiếu p thì hàm ném lỗi thay vì lấy mặc định, để bản ghi
rơi vào hàng chờ rà soát.

**A3 — hai đại lượng, hai công thức phương sai.**
Tương quan bậc không: `Var(r) = (1 − r²)² / (n − 1)`.
Tương quan riêng phần: `Var(r_p) = (1 − r_p²)² / df`.
Dùng nhầm công thức nghĩa là trọng số của nghiên cứu trong mô hình gộp sai,
và ước lượng gộp sai theo.

**Quyết định đã chốt (04/08/2026): bản ghi suy từ β mang
`metric_type = zero_order`** — Peterson & Brown hiệu chuẩn công thức bằng
cách khớp với r bậc không quan sát được (số hạng `.05·λ` tồn tại vì phép
khớp đó). `metric_type` mô tả *đại lượng cần ước lượng*; nguồn gốc con số
nằm ở hai trường riêng, tách thành ba lớp:

| Nguồn | metric_type | estimand_source | source_controls | Mô hình chính |
|---|---|---|---|---|
| r báo cáo | `zero_order` | `observed` | False | có |
| t hồi quy | `partial` | `observed` | True | có |
| β quy đổi | `zero_order` | `imputed_pb2005` | True | **không — chỉ độ nhạy** |

Bản ghi suy ra không vào mô hình chính vì `(1−r²)²/(n−1)` coi giá trị suy
ra như quan sát trực tiếp — bỏ qua sai số quy đổi nên trọng số vốn đã lớn
hơn mức đáng có. Trong R: β vào nhóm `ZCOR` nhưng mô hình chính lọc
`estimand_source == "observed"`.

Kèm theo A4: mọi bản ghi đều mang sẵn `fisher_z` và `var_z` để gộp trên
thang z rồi chuyển ngược khi báo cáo.

## Chạy

```bash
python3 test_effect_size.py            # 20/20 đạt, không cần pytest
python3 effect_size.py mau_cu.csv ra.csv
```

CSV đầu vào cần các cột `author, year, stat_type, value, n` và nên có
`n_predictors, df`. Đầu ra thêm mọi trường mới cùng hai cột `r_legacy` và
`delta_r` để đối chiếu.

## Kết quả trên bộ mẫu 10 bản ghi

| Nghiên cứu | Gốc | r cũ | r mới | Chênh | Đại lượng |
|---|---|---|---|---|---|
| Lu & Beamish | r 0.24 | 0.2400 | 0.2400 | +0.0000 | zero_order |
| Contractor et al. | t 2.14 | 0.1400 | 0.1428 | +0.0028 | partial |
| Pangarkar | t 1.98 | 0.1650 | 0.1698 | +0.0048 | partial |
| Chiao & Yang | β 0.18 | 0.1764 | 0.2264 | +0.0500 | zero_order (imputed) |
| Denis et al. | β −0.22 | −0.2156 | −0.2156 | +0.0000 | zero_order (imputed) |
| Nghien cuu Y | t 2.5 | 0.2724 | 0.2921 | +0.0197 | partial |
| Nghien cuu Z | β 0.62 | — | loại trừ | — | ngoài khoảng hợp lệ |

**5 bản ghi tăng, 0 bản ghi giảm.** Đây chính là dấu hiệu của lệch một
chiều: sai số cũ chỉ đẩy theo một hướng, nên ước lượng gộp bị hạ thấp một
cách có hệ thống chứ không phải nhiễu ngẫu nhiên.

Lưu ý về vai trò của bộ mẫu: phép so khớp từng byte giữa đầu ra
`recode_csv` và `mau_moi.csv` là **kiểm thử hồi quy** — nó chứng minh mã
chạy ổn định giữa các lần sửa, không chứng minh công thức đúng. Tính đúng
đắn nằm ở 20 kiểm thử tính tay; khi viết bài, dẫn các ví dụ tính tay chứ
không dẫn phép so khớp byte.

## Thế hệ khóa v8.0.0 — không ghi đè tập khóa v7.1.1

Sửa công thức nghĩa là các bản ghi đã khóa cho giá trị `r` khác — nhưng
tập v7.1.1 đã phát hành kèm DOI và tuyên bố cốt lõi của M-AIDA là bản ghi
khóa rồi thì không sửa. Vì vậy việc mã lại được xử lý như **một thế hệ
khóa mới**, không phải một bản sửa tại chỗ:

1. Tập khóa v7.1.1 giữ nguyên, không đụng vào.
2. Tập v8.0.0 sinh ra như một lần khóa độc lập; mỗi bản ghi mang con trỏ
   `derived_from` về bản ghi gốc v7.1.1.
3. Phát hành DOI phiên bản mới trên Zenodo, phần thay đổi ghi rõ đây là
   hiệu chỉnh công thức A1–A3.
4. Ghi vào nhật ký sai lệch OSF, vì đây là thay đổi so với kế hoạch đã
   đăng ký.

Cách làm này biến việc sửa lỗi thành bằng chứng cho chính hệ thống: phát
hiện được lỗi ở tầng công thức, truy ngược được ảnh hưởng tới từng bản
ghi, và phát hành lại mà không mất dấu vết.

## Lưu ý khi chạy bản R

Môi trường dựng gói này không có R cài sẵn nên bản R chưa chạy tại chỗ;
mọi giá trị kỳ vọng trong phần tự kiểm tra của nó trùng đúng với các ví
dụ tính tay đã chạy đạt ở bản Python. Chạy `Rscript analysis/effect_size.R`
một lần trước khi dùng. Kiểm tra lại tên tham số của `escalc` bằng
`?escalc` trước khi chạy khối metafor, vì metafor có thay đổi giữa các
phiên bản.
