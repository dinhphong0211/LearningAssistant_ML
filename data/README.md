# Dữ liệu

Thư mục này **không chứa dataset lớn**. Theo yêu cầu nộp bài, dữ liệu được chia sẻ bằng liên kết riêng, không nằm trong file zip mã nguồn.

## Nguồn dữ liệu đang dùng: D2L tiếng Việt

| Mục | Giá trị |
|---|---|
| Tên | *Dive into Deep Learning* (Đắm mình vào Học Sâu), bản dịch tiếng Việt |
| Trang đọc | https://vi.d2l.ai |
| Kho mã | https://github.com/d2l-ai/d2l-vi |
| Tác giả bản gốc | Aston Zhang, Zachary C. Lipton, Mu Li, Alexander J. Smola (arXiv:2106.11342) |
| Giấy phép | Sách: **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Mã mẫu: MIT. |
| Nơi xác nhận giấy phép | Mục "Giấy phép" trong README của https://github.com/d2l-ai/d2l-vi, mở lại ngày 04/10/2026. Trang chủ vi.d2l.ai không có mục giấy phép riêng. |
| Ngày tải | 04/10/2026 |

**Nghĩa vụ của CC BY-SA 4.0**: ghi nguồn (như bảng trên), ghi rõ nếu có chỉnh sửa, và nếu chia sẻ tài liệu phái sinh thì giữ cùng giấy phép. Văn bản trong `data/benchmark/` và `data/domain/` là bản chép nguyên văn từ sách, nên chia sẻ bằng link tới nguồn gốc hoặc kèm đúng ghi chú này; không đưa vào giấy phép MIT của mã nguồn.

## Bộ 1: benchmark tóm tắt (3 mục) — `data/benchmark/`

Mỗi mục gồm `<tên>.txt` (nội dung mục) và `<tên>.ref.txt` (phần "Tóm tắt" cuối mục trong sách, dùng làm tham chiếu). Tham chiếu do tác giả sách viết bằng tiếng Anh, bản tiếng Việt là bản dịch của nhóm dịch; **không phải do người làm đồ án viết**.

| File | Mục trong sách |
|---|---|
| `d2l_3_1` | 3.1. Hồi quy tuyến tính |
| `d2l_3_4` | 3.4. Hồi quy Softmax |
| `d2l_4_1` | 4.1. Multilayer Perceptrons |

## Bộ 2: phân loại lĩnh vực (12 mục) — `data/domain/<nhãn>/`

Nhãn lĩnh vực là **tên thư mục do người làm đồ án gán** (nhãn thay thế, không phải nhãn chuyên gia). 4 nhãn × 3 mục. Thư mục `data/domain/` nằm trong `.gitignore`.

| Nhãn (thư mục) | File | Mục trong sách |
|---|---|---|
| Machine Learning (`machine_learning/`) | `4_4_underfit_overfit` | 4.4. Lựa chọn mô hình, Underfitting, và Overfitting |
| | `4_5_weight_decay` | 4.5. Trọng lượng phân rã |
| | `4_9_distribution_shift` | 4.9. Môi trường và phân phối Shift |
| Deep Learning (`deep_learning/`) | `4_7_backprop` | 4.7. Chuyển tiếp tuyên truyền, tuyên truyền ngược, và đồ thị tính toán |
| | `6_1_why_conv` | 6.1. Từ các lớp được kết nối hoàn toàn đến sự phức tạp |
| | `7_5_batch_norm` | 7.5. Chuẩn hóa hàng loạt |
| Natural Language Processing (`nlp/`) | `8_3_language_models` | 8.3. Mô hình ngôn ngữ và bộ dữ liệu |
| | `14_1_word2vec` | 14.1. Từ nhúng (word2vec) |
| | `15_1_sentiment` | 15.1. Phân tích tình cảm và tập dữ liệu |
| Mathematics (`math/`) | `2_4_calculus` | 2.4. Calculus (Giải tích) |
| | `2_6_probability` | 2.6. Xác suất |
| | `18_5_integral_calculus` | 18.5. Integral Calculus |

Cách chia khi đánh giá: theo **tài liệu**, không theo đoạn, để các đoạn của cùng một mục không nằm ở cả tập huấn luyện và tập kiểm tra (xem `app/domain/ml_classifier.py`).

## Nguồn ứng viên đã cân nhắc, chưa dùng

Giấy phép ghi theo trang gốc ở lần đối chiếu ngày 03/10/2026; **mở lại trang gốc để xác nhận trước khi dùng**.

| Bộ dữ liệu | Nội dung | Giấy phép | Lý do chưa dùng |
|---|---|---|---|
| SciTLDR | 3.229 bài báo khoa học máy tính, TLDR một câu | Apache-2.0 (cần xác nhận trên dataset card `allenai/scitldr`) | Chỉ tiếng Anh, tóm tắt quá ngắn so với đầu ra của app |
| XL-Sum (tiếng Việt) | 40.137 bài BBC Tiếng Việt | CC BY-NC-SA 4.0, chỉ phi thương mại | Là tin tức, không phải tài liệu chuyên ngành |
| ViMs | 300 cụm, 1.945 bài báo tiếng Việt | Chưa xác minh | Đa văn bản, tin tức |
| VNDS | khoảng 150 nghìn bài báo tiếng Việt | Chưa xác minh | Tóm tắt tự động, không phải do người viết |

## Không đưa vào kho mã

`data/library.db` (thư viện bài học của người dùng), các file `.mp3`, `data/domain/`, và tài liệu có bản quyền không rõ quyền sử dụng.
