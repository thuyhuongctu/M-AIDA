# Chính sách nhánh

Cập nhật: 2026-08-04 · Trạng thái: **chờ điền nhánh đích** (quyết định của
chủ kho — xem mục đầu tiên; các quy tắc còn lại áp dụng được ngay).

## Nhánh đích

Nhánh đích duy nhất của kho này là: `[TÊN NHÁNH — chủ kho điền, quyết định
5 phút, không chờ dọn xong nhánh cũ]`

Mọi thay đổi đi vào kho qua nhánh này. Các nhánh hợp nhất khác được tuyên
bố **đã dừng** và không được tiếp tục phát triển.

## Lưu trữ nhánh: gắn thẻ trước, xóa sau

Không xóa nhánh trực tiếp. Quy trình chuẩn giữ nguyên toàn bộ commit:

```bash
# lưu trữ một nhánh
git tag archive/feat-xyz feat/xyz
git push origin archive/feat-xyz
git branch -D feat/xyz
git push origin --delete feat/xyz

# xem mọi nhánh đã lưu trữ
git tag -l 'archive/*'

# khôi phục khi cần
git branch feat/xyz archive/feat-xyz
```

Thẻ giữ nguyên lịch sử và luôn nhìn thấy được, nhưng danh sách nhánh sạch
đi. Với cách này, bản sao `--mirror` là lớp an toàn **thứ hai**, không phải
lớp duy nhất — nỗi lo mất việc khi phân loại gần như biến mất.

## Bản sao lưu trước khi dọn

Bản sao đầy đủ được tạo ngày [NGÀY] bằng:

```bash
git clone --mirror <repo> maida-backup-[NGÀY]
```

Mọi thao tác dọn dẹp sau ngày này đều đảo ngược được từ bản sao đó.

## Luật

1. Mọi thay đổi qua yêu cầu hợp nhất, không đẩy thẳng vào nhánh đích
2. Lưu trữ (gắn thẻ) rồi xóa nhánh ngay sau khi hợp nhất
3. Không quá mười nhánh mở cùng lúc
4. Tên nhánh theo dạng `loại/mô-tả-ngắn`, không dấu cách
5. Nhánh không có hoạt động quá sáu mươi ngày sẽ được lưu trữ

## Không làm

- Không chạy lệnh git phá hủy khi chưa gắn thẻ lưu trữ và chưa có bản sao
  mirror mới
- Không mở nhánh hợp nhất song song thứ hai

## Thứ tự

Chạy lệnh sao lưu → **chọn nhánh đích (làm ngay, việc 5 phút)** → điền tệp
này → rồi mới dọn 56 nhánh (việc nhiều giờ, làm song song hoặc sau — không
để nó chặn các việc khác).
