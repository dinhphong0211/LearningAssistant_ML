# Dữ liệu

Thư mục này **không chứa dataset lớn**. Theo yêu cầu nộp bài, dữ liệu được chia sẻ bằng liên kết riêng, không nằm trong file zip mã nguồn.

## Nguồn ứng viên (đã đối chiếu trang gốc ngày 03/10/2026)

Chưa tải và chưa chạy thực nghiệm với bộ nào. Mục "Giấy phép" lấy từ trang gốc nêu ở cột Nguồn; **hãy mở lại trang đó và xác nhận trước khi dùng hoặc chia sẻ**.

| Bộ dữ liệu | Nội dung | Bản tóm tắt | Giấy phép | Hợp với đồ án ở chỗ | Hạn chế |
|---|---|---|---|---|---|
| **D2L tiếng Việt** (Dive into Deep Learning, bản dịch) | Giáo trình học sâu tiếng Việt, theo chương/mục | Không có bộ tóm tắt sẵn; bạn tự viết | Sách: CC BY-SA 4.0; mã mẫu: MIT (theo README của repo d2l-vi) | Đúng lĩnh vực ML/DL, đúng tiếng Việt, có công thức và thuật ngữ | Phải tự viết tóm tắt tham chiếu. CC BY-SA yêu cầu ghi nguồn và giữ cùng giấy phép nếu bạn chia sẻ tài liệu phái sinh |
| **SciTLDR** | 3.229 bài báo khoa học máy tính (OpenReview) | 5.411 TLDR do tác giả và chuyên gia viết, mỗi TLDR một câu | Apache-2.0 (theo trang Papers with Code và một bài báo khác trích dẫn; cần xác nhận trên dataset card `allenai/scitldr`) | Có sẵn tài liệu + tóm tắt người viết, đúng lĩnh vực CS/ML, tiếng Anh | Chỉ tiếng Anh; tóm tắt rất ngắn (khoảng 15 đến 25 từ) nên không so trực tiếp với bản tóm tắt nhiều câu |
| **XL-Sum, phần tiếng Việt** | 40.137 bài báo BBC Tiếng Việt (32.111 train, 4.013 dev, 4.013 test) | Tóm tắt do biên tập viên BBC viết | CC BY-NC-SA 4.0, chỉ cho nghiên cứu phi thương mại | Có sẵn cả hai phía, tiếng Việt, đủ lớn | Là tin tức, **không phải tài liệu chuyên ngành**; chỉ dùng kiểm tra luồng tiếng Việt, không chứng minh được chất lượng với tài liệu học tập |
| **ViMs** | 300 cụm, 1.945 bài báo tiếng Việt | 600 bản tóm tắt đa văn bản do người viết | Chưa xác minh | Tóm tắt do người viết, tiếng Việt | Tin tức, đa văn bản (khác bài toán của app); chưa biết cách tải và giấy phép |
| **VNDS** | Khoảng 150 nghìn bài báo tiếng Việt | **Tự động** lấy từ đoạn mở đầu, không phải người viết | Chưa xác minh | Quy mô lớn | **Không dùng làm bản tham chiếu**: ThucHien.txt yêu cầu tham chiếu do người viết |

## Đề xuất bộ thử nghiệm nhỏ (khả thi trong thời gian còn lại)

1. **5 đến 10 mục từ D2L tiếng Việt** (đúng lĩnh vực, đúng ngôn ngữ). Với mỗi mục, bạn tự viết 5 đến 10 câu tóm tắt tham chiếu **không dùng AI**. Đây là bộ chính cho phần kết quả.
2. **20 mẫu SciTLDR (bản AIC)**: kiểm tra trên tài liệu khoa học tiếng Anh, bản tham chiếu có sẵn. Để so công bằng, cho cả ba phương pháp tạo bản tóm tắt cùng độ dài ngắn (1 đến 2 câu).
3. **20 mẫu XL-Sum tiếng Việt (tập test)**: chỉ để kiểm tra luồng tiếng Việt và TTS, ghi rõ trong báo cáo là dữ liệu tin tức.

Lưu ý về cách đọc kết quả: tham chiếu của SciTLDR và XL-Sum rất ngắn, còn bản tóm tắt của app thường dài hơn, nên ROUGE sẽ thấp và dễ gây hiểu lầm. Hãy so các phương pháp với nhau trên cùng độ dài, đừng so với con số trong các bài báo.

## Việc phải làm trước khi dùng

- [ ] Mở trang gốc từng bộ, chép nguyên giấy phép vào bảng dưới.
- [ ] Ghi ngày tải và phiên bản.
- [ ] Chia train / validation / test và đảm bảo cùng một tài liệu không nằm ở hai tập.

| Bộ dữ liệu | Link trang gốc | Giấy phép (đã xác nhận) | Ngày tải | Đường dẫn trong project |
|---|---|---|---|---|
| D2L-vi | https://github.com/d2l-ai/d2l-vi | | | |
| SciTLDR | https://aclanthology.org/2020.findings-emnlp.428/ (bài báo) | | | |
| XL-Sum | https://github.com/csebuetnlp/xl-sum | | | |

## Không đưa vào kho mã

`data/library.db` (thư viện bài học của người dùng, đã nằm trong `.gitignore`), các file `.mp3`, và tài liệu có bản quyền không rõ quyền sử dụng.
