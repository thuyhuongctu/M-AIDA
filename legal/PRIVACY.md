# M-AIDA Privacy Policy (closed beta)

Effective date: [date the beta opens]. Version 1.0-beta.

Vietnamese version below (Bản tiếng Việt ở phần sau). This policy explains what the M-AIDA hosted service collects, why, where it goes and for how long. It is written to be checked against the code: every item below corresponds to a table or a log in the open-source backend (https://github.com/thuyhuongctu/M-AIDA, `backend/db.py`).

## 1. Controller

The data controller during the closed beta is Đỗ Thùy Hương, Vietnam, thuyhuongctu@gmail.com ("the Operator"). Requests about your data go to that address.

## 2. What we collect and why

Account: your e-mail address, the display name your sign-in provider supplies, the account identifier, sign-in times, and whether you are a beta account. Purpose: to let you sign in and to keep your records separate from other users'.

Extraction records: the fields extracted from each paper (sample size, effect statistics, measures, the page numbers and the verbatim sentences quoted as evidence), the model's original proposal, your corrections, approval and lock decisions, and your notes. Purpose: this is the product; it is what you come back to verify and export.

Job records: for each upload, the file name, size in bytes, page count, the metadata you typed (title, authors, year, country), timestamps, the outcome (succeeded, rejected, failed) and the error message. Purpose: to show you what happened and to refund credits when the failure is ours.

Model-call records: for each call to the language model, the model name, the number of input and output tokens, latency and an estimated cost. Purpose: cost accounting for the beta and for setting a fair price later. These records contain no paper text.

Credit ledger: every credit movement (grant, use, refund) with its reason and the balance after it. Purpose: the balance you see and the record behind it.

Audit log: which account performed which action (extract, verify, lock, export, delete, grant) on which record, and when. Purpose: integrity of the verified data set; it lets a reviewer see that a locked record was not altered afterwards.

Server logs: the usual web-server records (IP address, time, path, status) kept for security and debugging, rotated after a short period. They never contain PDF text or quotations.

## 3. What we do not keep

The PDF you upload is read into memory, its text is sent to the model provider, and the file is discarded when the extraction finishes, whatever the outcome. It is never written to disk or to the database. If you need the paper again, keep your own copy. Beyond the verbatim evidence sentences and page numbers that become part of a record, the paper's text is not retained.

## 4. Where the data goes (processors)

To run the service we use the following providers, each of which processes data on our instructions: Supabase, Inc. (user sign-in and the database; the database for this service is hosted in the Asia-Pacific region stated in the application's configuration); Anthropic, PBC (the language model: the text of each uploaded paper and the extraction prompt are sent to Anthropic's API in the United States for the duration of the call; under Anthropic's commercial API terms this data is not used to train its models); the hosting provider of our server (named in the application's configuration page once the beta opens); and the e-mail delivery used for sign-in links. We do not sell personal data and do not use advertising trackers. The transfer of paper text and account data outside Vietnam is necessary to provide the service; by using it you consent to that transfer as described here.

## 5. Legal basis

We process your data on the basis of your consent given when you sign in and accept the Terms, and of the need to perform the service you asked for. Vietnamese law on personal data protection (including Decree 13/2023/NĐ-CP and the Law on Personal Data Protection in force from 2026) applies to users in Vietnam; where the GDPR or a similar law applies to you, the same bases (consent, contract) are relied on.

## 6. How long we keep it

Account, records, jobs, ledger and audit entries are kept while your account exists. When you ask us to delete your account we remove the account, its unlocked records and job metadata within 30 days. Locked records are deleted as well unless you have exported them and ask us to keep an anonymised copy for the validation study; we do not keep them without that request. Aggregated statistics (counts, rates, costs) that cannot identify you are kept. Model-call and ledger records are kept for accounting for the period required by law, without the e-mail address once the account is gone. Server logs are rotated within 30 days.

## 7. Your rights

You can see your records at any time in the application and download everything we hold about you (records, jobs, ledger) as a JSON file from the Account tab. You can ask us to correct account data, to delete your account, to restrict processing, or to explain any processing, by e-mail to the address in section 1; we answer within 30 days. You may withdraw consent by stopping use and asking for deletion. If you believe we handle your data unlawfully, you may complain to the competent Vietnamese authority (the Ministry of Public Security's data protection authority) or to the authority of your own country.

## 8. Security

Connections are encrypted (TLS). Sign-in uses one-time e-mail links or Google; we never see or store a password. The server verifies your session locally and filters every query by your account. The model-provider key lives only on the server. The database is backed up daily by the database provider. Access to the server and the database is limited to the Operator. We will notify affected users without undue delay of any breach that affects their data.

## 9. Children

The service is for adults engaged in research. We do not knowingly collect data from anyone under 18.

## 10. Changes

We may update this policy; the version and effective date at the top change when we do, and material changes are announced by e-mail or in the application 15 days before they apply.

---

# Chính sách riêng tư M-AIDA (beta kín)

Ngày hiệu lực: [ngày mở beta]. Phiên bản 1.0-beta.

Chính sách này giải thích dịch vụ M-AIDA thu thập gì, vì sao, gửi đi đâu và giữ bao lâu. Mỗi mục dưới đây tương ứng với một bảng hoặc nhật ký trong mã nguồn mở của backend (https://github.com/thuyhuongctu/M-AIDA, `backend/db.py`) để có thể đối chiếu.

## 1. Bên kiểm soát dữ liệu

Trong giai đoạn beta kín, bên kiểm soát dữ liệu là bà Đỗ Thùy Hương, Việt Nam, thuyhuongctu@gmail.com ("Bên vận hành"). Mọi yêu cầu về dữ liệu của bạn gửi tới địa chỉ này.

## 2. Thu thập gì và để làm gì

Tài khoản: địa chỉ e-mail, tên hiển thị do nhà cung cấp đăng nhập chuyển sang, mã định danh tài khoản, thời điểm đăng nhập, và dấu tài khoản beta. Mục đích: để bạn đăng nhập và để tách bản ghi của bạn khỏi người dùng khác.

Bản ghi trích xuất: các trường trích từ mỗi bài báo (cỡ mẫu, thống kê hiệu ứng, thang đo, số trang và câu nguyên văn được trích làm bằng chứng), đề xuất gốc của mô hình, các chỉnh sửa, quyết định phê duyệt và khóa của bạn, ghi chú của bạn. Mục đích: đây chính là sản phẩm, là thứ bạn quay lại để kiểm tra và xuất.

Bản ghi job: với mỗi lần tải lên, tên tệp, kích thước, số trang, siêu dữ liệu bạn nhập (tiêu đề, tác giả, năm, quốc gia), mốc thời gian, kết quả (thành công, từ chối, lỗi) và thông điệp lỗi. Mục đích: cho bạn biết chuyện gì đã xảy ra và hoàn tín dụng khi lỗi thuộc về chúng tôi.

Bản ghi gọi mô hình: với mỗi lần gọi mô hình ngôn ngữ, tên mô hình, số token vào và ra, độ trễ và chi phí ước tính. Mục đích: hạch toán chi phí trong beta và định giá hợp lý sau này. Bản ghi này không chứa văn bản bài báo.

Sổ tín dụng: mọi biến động tín dụng (cấp, dùng, hoàn) kèm lý do và số dư sau đó. Mục đích: số dư bạn thấy và căn cứ của nó.

Nhật ký kiểm toán: tài khoản nào thực hiện thao tác nào (trích xuất, duyệt, khóa, xuất, xóa, cấp tín dụng) trên bản ghi nào, lúc nào. Mục đích: bảo đảm tính toàn vẹn của bộ dữ liệu đã kiểm tra; người phản biện có thể thấy bản ghi đã khóa không bị sửa sau đó.

Nhật ký máy chủ: bản ghi web thông thường (địa chỉ IP, thời gian, đường dẫn, mã trạng thái) để bảo mật và gỡ lỗi, xoay vòng sau thời gian ngắn. Không bao giờ chứa văn bản PDF hay câu trích.

## 3. Những gì chúng tôi không giữ

PDF bạn tải lên được đọc trong bộ nhớ, văn bản của nó được gửi tới nhà cung cấp mô hình, và tệp bị hủy khi trích xuất kết thúc, dù kết quả thế nào. Tệp không bao giờ được ghi xuống đĩa hay cơ sở dữ liệu. Nếu cần bài báo, bạn hãy giữ bản của mình. Ngoài các câu bằng chứng nguyên văn và số trang trở thành một phần của bản ghi, văn bản bài báo không được lưu.

## 4. Dữ liệu đi đâu (bên xử lý)

Để vận hành dịch vụ, chúng tôi dùng các nhà cung cấp sau, mỗi bên xử lý dữ liệu theo chỉ dẫn của chúng tôi: Supabase, Inc. (đăng nhập và cơ sở dữ liệu; cơ sở dữ liệu của dịch vụ đặt tại khu vực Châu Á - Thái Bình Dương nêu trong cấu hình ứng dụng); Anthropic, PBC (mô hình ngôn ngữ: văn bản của mỗi bài báo tải lên và lời nhắc trích xuất được gửi tới API của Anthropic tại Hoa Kỳ trong thời gian xử lý; theo điều khoản API thương mại của Anthropic, dữ liệu này không được dùng để huấn luyện mô hình); nhà cung cấp máy chủ (nêu tên trong trang cấu hình của ứng dụng khi mở beta); và dịch vụ gửi e-mail cho liên kết đăng nhập. Chúng tôi không bán dữ liệu cá nhân và không dùng trình theo dõi quảng cáo. Việc chuyển văn bản bài báo và dữ liệu tài khoản ra ngoài Việt Nam là cần thiết để cung cấp dịch vụ; khi dùng dịch vụ, bạn đồng ý với việc chuyển này như mô tả ở đây.

## 5. Căn cứ pháp lý

Chúng tôi xử lý dữ liệu của bạn trên cơ sở sự đồng ý của bạn khi đăng nhập và chấp nhận Điều khoản, và trên cơ sở cần thiết để thực hiện dịch vụ bạn yêu cầu. Pháp luật Việt Nam về bảo vệ dữ liệu cá nhân (gồm Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân có hiệu lực từ năm 2026) áp dụng với người dùng tại Việt Nam; nếu GDPR hoặc luật tương tự áp dụng với bạn, các căn cứ tương ứng (đồng ý, hợp đồng) được viện dẫn.

## 6. Giữ bao lâu

Tài khoản, bản ghi, job, sổ tín dụng và nhật ký kiểm toán được giữ chừng nào tài khoản còn tồn tại. Khi bạn yêu cầu xóa tài khoản, chúng tôi xóa tài khoản, các bản ghi chưa khóa và siêu dữ liệu job trong 30 ngày. Bản ghi đã khóa cũng bị xóa, trừ khi bạn đã xuất và đề nghị chúng tôi giữ một bản ẩn danh cho nghiên cứu đánh giá; không có đề nghị đó chúng tôi không giữ. Số liệu tổng hợp (số lượng, tỷ lệ, chi phí) không định danh được bạn thì được giữ. Bản ghi gọi mô hình và sổ tín dụng được giữ cho mục đích kế toán trong thời hạn pháp luật yêu cầu, không kèm địa chỉ e-mail sau khi tài khoản đã xóa. Nhật ký máy chủ xoay vòng trong 30 ngày.

## 7. Quyền của bạn

Bạn xem được bản ghi của mình bất kỳ lúc nào trong ứng dụng và tải về toàn bộ dữ liệu chúng tôi giữ về bạn (bản ghi, job, sổ tín dụng) dạng JSON ở thẻ Tài khoản. Bạn có thể yêu cầu sửa dữ liệu tài khoản, xóa tài khoản, hạn chế xử lý, hoặc giải thích về việc xử lý, qua e-mail tới địa chỉ ở mục 1; chúng tôi trả lời trong 30 ngày. Bạn rút lại sự đồng ý bằng cách ngừng sử dụng và yêu cầu xóa. Nếu cho rằng chúng tôi xử lý dữ liệu trái pháp luật, bạn có thể khiếu nại tới cơ quan có thẩm quyền tại Việt Nam (cơ quan bảo vệ dữ liệu cá nhân thuộc Bộ Công an) hoặc cơ quan của nước bạn.

## 8. Bảo mật

Kết nối được mã hóa (TLS). Đăng nhập bằng liên kết e-mail dùng một lần hoặc Google; chúng tôi không bao giờ thấy hay lưu mật khẩu. Máy chủ xác minh phiên của bạn tại chỗ và lọc mọi truy vấn theo tài khoản của bạn. Khóa nhà cung cấp mô hình chỉ nằm trên máy chủ. Cơ sở dữ liệu được nhà cung cấp sao lưu hằng ngày. Quyền truy cập máy chủ và cơ sở dữ liệu giới hạn ở Bên vận hành. Chúng tôi sẽ thông báo cho người dùng bị ảnh hưởng không chậm trễ về bất kỳ sự cố nào liên quan tới dữ liệu của họ.

## 9. Trẻ em

Dịch vụ dành cho người trưởng thành làm nghiên cứu. Chúng tôi không cố ý thu thập dữ liệu của người dưới 18 tuổi.

## 10. Thay đổi

Chúng tôi có thể cập nhật chính sách này; số phiên bản và ngày hiệu lực ở đầu trang sẽ thay đổi, và thay đổi quan trọng được thông báo qua e-mail hoặc trong ứng dụng 15 ngày trước khi áp dụng.
