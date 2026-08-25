# Chạy bản M-AIDA thật để trình diễn trước hội đồng

> Thư mục `demo/` chỉ là bộ đóng gói trình diễn: nó khởi động đúng backend
> FastAPI trong `backend/` (phiên bản 7.1.x, không sửa mã lõi) và nạp sẵn
> dữ liệu thật từ cơ sở dữ liệu phân tích P6 đã khóa của luận án.
> Không có phản hồi nào được mô phỏng; mọi thao tác đều đi qua API thật.

## 1. Yêu cầu

- Python 3.11 trở lên, kết nối mạng lần đầu để cài thư viện.
- Không cần Node.js, không cần Docker (giao diện demo là một tệp HTML
  do chính backend phục vụ; giao diện React đầy đủ vẫn ở `frontend/`).

## 2. Cách chạy (3 lệnh)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
python demo/run_defense.py
```

Mở trình duyệt tại `http://localhost:8765/`. Tài liệu API tự sinh (OpenAPI)
ở `http://localhost:8765/docs`.

## 3. Dữ liệu được nạp

- Mặc định: `demo/demo_seed.csv` gồm 18 dòng mức độ ảnh hưởng thật của
  13 nghiên cứu đã công bố, trích nguyên văn từ cơ sở dữ liệu P6 đã khóa
  (trong đó có các nghiên cứu của chính nhóm tác giả tại Việt Nam,
  Thổ Nhĩ Kỳ, Ba Lan, Ấn Độ, Trung Quốc).
- Dòng có r báo cáo trực tiếp được nạp ở trạng thái ĐÃ KHÓA (đúng trạng
  thái của chúng trong luận án). Ba dòng có r theo đường ước lượng
  (S189, S190, S191) được để ở trạng thái CHỜ KIỂM CHỨNG kèm ảnh chụp
  "đề xuất của máy" bất biến, để trình diễn trực tiếp quy trình
  người kiểm chứng.
- Muốn nạp TOÀN BỘ cơ sở dữ liệu 286 dòng (tệp này không nằm trong kho
  công khai cho tới khi luận án công bố):

```bash
MAIDA_SEED_CSV=/duong/dan/p6_study_database.csv python demo/run_defense.py
```

  Thêm `MAIDA_LOCK_ALL=1` nếu muốn khóa cả các dòng ước lượng.

## 4. Kịch bản trình diễn 5 phút trước hội đồng

1. Mở trang chính: thanh trạng thái cho thấy phiên bản, số bản ghi,
   và tình trạng khóa API trích xuất (thật, đọc từ `/api/health`).
2. Lọc "Needs review", chọn S190 (Thổ Nhĩ Kỳ, nghiên cứu của nhóm):
   bảng "Machine proposal" hiển thị giá trị máy đề xuất cạnh giá trị
   hiện hành.
3. Sửa thử một trường (ví dụ r), ghi chú kiểm chứng vào ô PI notes,
   bấm "Approve & save": lệnh PATCH `/verify` thật được ghi nhận,
   cột trạng thái đổi thành "approved".
4. Bấm "Lock record": bản ghi bị khóa vĩnh viễn. Bấm "Approve & save"
   lần nữa để hội đồng thấy server trả về đúng mã 409 Conflict
   (khóa được thực thi ở phía server, không phải giao diện).
5. Bấm "Export locked CSV": tải về tệp CSV do backend sinh từ đúng các
   bản ghi đã khóa.
6. Nếu hội đồng hỏi về trích xuất PDF thật: khi `backend/.env` có
   `LLM_API_KEY`, kéo một bài PDF vào ô "Extract a new PDF" để chạy
   pipeline mô hình ngôn ngữ thật; khi không có khóa, server trả 503
   với thông báo rõ ràng (không giả lập kết quả).

## 5. Trả lời nhanh nếu hội đồng hỏi

- "Đây có phải mô phỏng không?" Không. Trang này gọi thẳng các endpoint
  FastAPI trong `backend/main.py`; có thể mở `/docs` và bấm thử từng
  endpoint để đối chứng.
- "Dữ liệu ở đâu ra?" Trích nguyên văn từ cơ sở dữ liệu phân tích P6 đã
  được nghiên cứu sinh kiểm chứng và khóa; quy tắc nạp ghi trong docstring
  của `demo/run_defense.py` (không bịa thêm trường nào).
- "Vì sao bản demo công khai trên web lại mô phỏng trích xuất?" Vì trích
  xuất thật cần khóa API mô hình ngôn ngữ và chi phí gọi mô hình; bản
  tự vận hành này chạy pipeline thật khi người dùng cung cấp khóa riêng.
- "Lưu trữ thế nào?" Phiên bản 7.1.x lưu trong bộ nhớ tiến trình (ghi rõ
  trong mã nguồn và bài báo); lưu SQLite nằm trong đặc tả 7.2.

## 6. Diễn tập trước ngày bảo vệ

Chạy thử toàn bộ kịch bản mục 4 ít nhất một lần trên chính máy sẽ mang
đi bảo vệ, khi KHÔNG có mạng (sau khi đã cài thư viện): toàn bộ demo
hoạt động ngoại tuyến, trừ bước trích xuất PDF thật cần mạng.


## 7. Defense App v1: PIN, lưu trạng thái và khôi phục

Khi khởi động, terminal in ra một **Presenter PIN** ngẫu nhiên. Giao diện chỉ
yêu cầu PIN khi có thao tác làm thay đổi dữ liệu (trích xuất, xác minh, khóa,
reset). Các thao tác đọc, lọc và xuất dữ liệu vẫn hoạt động bình thường.

- Trạng thái phiên được lưu tại `demo/.defense-state.json` và tự khôi phục sau
  khi khởi động lại.
- Nút **Reset demo** đưa ứng dụng về đúng bộ dữ liệu P6 mẫu đã kiểm chứng.
- Nút **Defense mode** bật giao diện toàn màn hình, chữ lớn và header cố định.
- Chỉ báo **network** giúp người trình bày biết đang online hay dùng app shell
  offline.
- Có thể đặt PIN cố định trước buổi bảo vệ:

```bash
MAIDA_DEMO_PIN=2468 python demo/run_defense.py
```

Trên Windows PowerShell:

```powershell
$env:MAIDA_DEMO_PIN="2468"
python demo/run_defense.py
```

Không đưa PIN thật vào Git hoặc slide công khai.

## 8. Cài như ứng dụng trên máy/điện thoại

Khi trang `http://localhost:8765/` được mở bằng Chrome/Edge trên máy chạy
demo, chọn **Install app / Cài đặt ứng dụng** từ menu trình duyệt. App shell,
manifest và service worker được phục vụ trực tiếp bởi FastAPI.

Để trình diễn trên điện thoại trong cùng mạng, chạy laptop và điện thoại trên
cùng Wi-Fi/hotspot, mở địa chỉ LAN của laptop, ví dụ
`http://192.168.1.10:8765/`. Một số trình duyệt chỉ cho phép cài PWA đầy đủ
trên HTTPS; vì vậy laptop cục bộ vẫn là thiết bị trình diễn chính, điện thoại là
màn hình phụ.

## 9. Kịch bản trình diễn 6 phút

1. **0:00–0:45:** mở Dashboard, nêu dữ liệu thật và nguồn P6 đã khóa.
2. **0:45–1:45:** lọc bản ghi locked/pending và giải thích ba đường chuyển đổi.
3. **1:45–3:30:** chọn một bản ghi pending, đối chiếu machine proposal, nhập
   ghi chú PI và phê duyệt.
4. **3:30–4:15:** khóa bản ghi; thử sửa lại để chứng minh API trả 409.
5. **4:15–5:00:** xuất CSV đã khóa và mở tài liệu API.
6. **5:00–6:00:** nếu có mạng, chạy PDF mẫu; nếu không, chỉ báo offline chứng
   minh phần kiểm chứng, khóa và xuất dữ liệu vẫn hoạt động.

## 10. Checklist trước khi vào phòng

- Chạy `python demo/smoke_test.py`.
- Khởi động app, ghi Presenter PIN vào giấy riêng.
- Nhấn **Reset demo** và kiểm tra số locked/pending.
- Mở sẵn một bản ghi pending.
- Chuẩn bị PDF mẫu nhưng không phụ thuộc vào live LLM.
- Tắt thông báo hệ điều hành; cắm nguồn laptop.
- Giữ một bản CSV export dự phòng và ảnh chụp màn hình kết quả.
