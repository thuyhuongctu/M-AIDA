# M-AIDA · Bước 1 — Sửa ba công thức A1–A3

Gói mã thay thế cho tầng chuyển đổi cỡ ảnh hưởng của M-AIDA v7.1.1.
Bản backend (`backend/extractor.py`) đã được đồng bộ theo đúng ngữ nghĩa
của gói này; module ở đây là bản chuẩn độc lập dùng cho việc mã lại
dữ liệu và cho pipeline R.

| Tệp | Nội dung |
|---|---|
| `effect_size.py` | Module Python đã sửa, kèm bộ mã lại CSV (`recode_csv`) |
| `test_effect_size.py` | 19 kiểm thử đơn vị, mọi giá trị kỳ vọng đều tính tay |
| `effect_sizes.R` | Bản R tương đương (testthat: `test_effect_sizes.R`) |
| `mau_cu.csv` · `mau_moi.csv` | Bộ dữ liệu mẫu trước và sau khi mã lại |

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
và ước lượng gộp sai theo. β đã kiểm soát các biến khác nên bản ghi suy từ
β mang `metric_type = partial`.

Kèm theo A4: mọi bản ghi đều mang sẵn `fisher_z` và `var_z` để gộp trên
thang z rồi chuyển ngược khi báo cáo.

## Chạy

```bash
python3 test_effect_size.py            # 19/19 đạt, không cần pytest
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
| Chiao & Yang | β 0.18 | 0.1764 | 0.2264 | +0.0500 | partial |
| Denis et al. | β −0.22 | −0.2156 | −0.2156 | +0.0000 | partial |
| Nghien cuu Y | t 2.5 | 0.2724 | 0.2921 | +0.0197 | partial |
| Nghien cuu Z | β 0.62 | — | loại trừ | — | ngoài khoảng hợp lệ |

**5 bản ghi tăng, 0 bản ghi giảm.** Đây chính là dấu hiệu của lệch một
chiều: sai số cũ chỉ đẩy theo một hướng, nên ước lượng gộp bị hạ thấp một
cách có hệ thống chứ không phải nhiễu ngẫu nhiên.

## Lưu ý

Môi trường dựng gói này không có R cài sẵn nên bản R chưa chạy tại chỗ;
mọi giá trị kỳ vọng trong test R trùng đúng với các ví dụ tính tay đã chạy
đạt ở bản Python. Chạy
`Rscript -e 'testthat::test_file("analysis/test_effect_sizes.R")'`
một lần trước khi dùng. Khung quy trình metafor cho bước 5–7 (mô hình ba
cấp so với hai cấp, phương sai vững theo cụm, khoảng dự báo, bảng nhiều
ước lượng thiên lệch, kiểm định giả thuyết chữ S) sẽ bổ sung ở bước 5;
kiểm tra lại tên tham số của `escalc` bằng `?escalc` trước khi chạy, vì
metafor có thay đổi giữa các phiên bản.
