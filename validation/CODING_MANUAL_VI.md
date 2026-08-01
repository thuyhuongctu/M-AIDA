# Sổ tay mã hóa kiểm định độc lập M-AIDA

## 1. Vai trò và làm mù

- Coder 1 và Coder 2 đọc toàn văn độc lập, không xem machine proposal và
  không xem phiếu của nhau trước khi hoàn tất lần mã hóa đầu.
- Người phân xử chỉ mở hai phiếu sau khi cả hai đã đóng dấu hoàn tất.
- Người chạy M-AIDA không thay đổi model, prompt, temperature hay extraction
  rules sau khi sampling frame được khóa.

## 2. Đơn vị mã hóa

Đơn vị là một **candidate effect**, không phải chỉ một bài báo. Trong mỗi bài,
coder ghi cả:

- hệ số I–P trọng tâm đủ điều kiện;
- hệ số I–P khác nếu bài có nhiều mẫu hoặc nhiều thước đo;
- ít nhất một hệ số gây nhiễu phù hợp khi có, chẳng hạn control, interaction,
  mediator hoặc outcome không trọng tâm.

Thiết kế này tạo được true positive, false positive và false negative thật để
tính precision/recall; chỉ nhập các effect đã biết đúng sẽ làm benchmark thiên lệch.

## 3. Trường bắt buộc

Với từng candidate effect, ghi `case_id`, `paper_id`, `effect_id`, vị trí nguồn
(trang, bảng, mô hình, dòng/cột), quyết định in-scope, conversion route, giá trị
`r`, `N`, DOI measure, performance measure, thời gian và ghi chú.

Quy ước route:

- `direct_r`: bài báo trực tiếp Pearson r;
- `t_to_r`: chuyển đổi từ t và df;
- `beta_to_r`: chuyển đổi từ standardized beta theo protocol;
- `other`: tuyến khác đã được protocol cho phép và mô tả đầy đủ;
- để trống route khi candidate effect được phân xử là out-of-scope.

## 4. Phân xử

1. So sánh coder 1 và coder 2 theo từng `case_id`.
2. Đánh dấu bất đồng nhưng không sửa đè phiếu gốc.
3. Mở đúng vị trí nguồn trong full text.
4. Ghi quyết định đồng thuận vào cột `gold_*` và lý do vào
   `adjudication_notes`.
5. Khóa gold standard trước khi ghép với predictions của M-AIDA.

## 5. Ranh giới diễn giải

Benchmark chỉ đánh giá chuẩn bị dữ liệu effect size. Nó không đánh giá quy
trình screening, risk-of-bias, mô hình meta-analysis hoặc diễn giải kết quả P6.
Mọi kết quả dưới ngưỡng phải được giữ lại và báo cáo; không thay mẫu, prompt
hoặc tolerance sau khi xem kết quả.

## Tài liệu tham khảo

Page, M. J., McKenzie, J. E., Bossuyt, P. M., Boutron, I., Hoffmann, T. C.,
Mulrow, C. D., Shamseer, L., Tetzlaff, J. M., Akl, E. A., Brennan, S. E., Chou,
R., Glanville, J., Grimshaw, J. M., Hróbjartsson, A., Lalu, M. M., Li, T.,
Loder, E. W., Mayo-Wilson, E., McDonald, S., ... Moher, D. (2021). The PRISMA
2020 statement: An updated guideline for reporting systematic reviews. *BMJ,
372*, n71. https://doi.org/10.1136/bmj.n71

Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M.,
Baak, A., Blomberg, N., Boiten, J.-W., da Silva Santos, L. B., Bourne, P. E.,
Bouwman, J., Brookes, A. J., Clark, T., Crosas, M., Dillo, I., Dumon, O.,
Edmunds, S., Evelo, C. T., Finkers, R., ... Mons, B. (2016). The FAIR Guiding
Principles for scientific data management and stewardship. *Scientific Data,
3*, Article 160018. https://doi.org/10.1038/sdata.2016.18
