# Tầm nhìn M-AIDA 8.0 (một trang, chỉ định hướng)

8.0 chỉ khởi động sau khi 7.1.1 được kiểm định trên bộ chuẩn vàng và 7.2 phát hành.
Đây là thay đổi kiến trúc lớn theo Semantic Versioning, trình bày như chương trình
nghiên cứu, không phải cam kết tính năng.

## Kiến trúc mục tiêu

Evidence ingestion -> Document parsing -> Citation-grounded extraction ->
Human verification -> Immutable evidence store -> Statistical orchestration ->
Reproducible outputs

## Các mô đun dự kiến

Discovery; Screening; Full-text eligibility; Extraction; Coding; Risk-of-bias assessment;
Data provenance; Statistical orchestration; PRISMA reporting; Living review updates;
Manuscript evidence tables.

## Nguyên tắc bất biến

1. Hệ thống sinh script và cấu hình; người nghiên cứu kiểm tra và kích hoạt; kết quả
   lưu cùng mã, phiên bản gói và seed. Không có "AI tự kết luận".
2. Mọi giá trị truy vết được về nguồn ở cấp trang, bảng hoặc đoạn.
3. Con người trong vòng quyết định, khả năng giải thích, khả năng tái lập, liêm chính
   nghiên cứu, bằng chứng minh bạch (năm nguyên tắc của khung AAMF được đề xuất trong
   luận án, ở mức định hướng).
