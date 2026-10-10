# Test cases 

Cột **Actual Output** chỉ ghi kết quả đã thực sự chạy.

- **Test tự động:** chạy lại ngày 04/10/2026 bằng `pytest -q`: **152 test đạt, 0 lỗi, 1 cảnh báo** (`FutureWarning`: thư viện `google-generativeai` đã ngừng hỗ trợ, Google khuyến nghị chuyển sang `google.genai`). Lệnh chạy ở cuối tài liệu.
- **Test thủ công:** chạy ngày 04/10/2026 trên giao diện Streamlit với tài liệu `data/benchmark/d2l_3_4.txt` (19.8 KB), model tóm tắt `gemini-flash-lite-latest`, giọng đọc HoaiMy (vi-VN). Ảnh chụp lưu trong `screenshots/`.
- TC12 và TC13 có kết quả thủ công không như kỳ vọng và được ghi nguyên văn; TC15, TC16 chỉ hỗ trợ một phần theo thiết kế.

| ID | Input | Expected Output | Actual Output | Status |
|---|---|---|---|---|
| TC01 | PDF có text layer (`data/sample.pdf`) | Trích xuất được đoạn văn, không rỗng | Thủ công: tải `data/sample.pdf`, trích xuất được văn bản, không rỗng | ✅ Thủ công |
| TC02 | DOCX có đoạn và bảng | Giữ thứ tự, bảng thành hàng `a \| b` | `test_loader::test_docx_paragraphs_and_tables` đạt | ✅ Tự động |
| TC03 | PPTX có text, bảng, ghi chú | Có text từng slide và ghi chú, đúng số slide | `test_loader::test_pptx_text_notes_and_pages` đạt | ✅ Tự động |
| TC04 | TXT UTF-8 | Đọc đúng tiếng Việt, tách đoạn | `test_loader::test_txt_utf8` đạt. Thủ công: tải `d2l_3_4.txt` (19.8 KB), app xử lý được, loại file `txt`, chia thành 3 đoạn | ✅ Tự động + thủ công |
| TC05 | PNG/JPG | OCR trả văn bản | Tự động: `test_image_with_fake_ocr` đạt. Thủ công: tải ảnh PNG/JPG, OCR bằng Gemini thật trả về văn bản | ✅ Tự động + thủ công |
| TC06 | PDF scan (không text layer) | Tự chuyển sang OCR, cảnh báo giới hạn 10 trang | Thủ công: tải PDF scan, app tự chuyển sang OCR và hiển thị cảnh báo giới hạn 10 trang | ✅ Thủ công |
| TC07 | File rỗng 0 byte | Báo lỗi tiếng Việt, không treo | `test_loader::test_empty_file` đạt | ✅ Tự động |
| TC08 | DOCX hỏng | `DocumentError` thân thiện | `test_loader::test_corrupted_docx` đạt | ✅ Tự động |
| TC09 | Tài liệu rất dài | Chia đoạn có overlap, map-reduce không vượt giới hạn | Chia đoạn: `test_chunker` đạt. Thủ công: xử lý tài liệu dài bằng map-reduce với Gemini thật, không vượt giới hạn | ✅ Tự động + thủ công |
| TC10 | Tài liệu tiếng Việt | Nhận diện ngôn ngữ, lĩnh vực, thuật ngữ | Tự động: `test_pipeline_specialized::test_specialized_fields_present`, `test_detector::test_language_detection` đạt. Thủ công với `d2l_3_4`: ngôn ngữ nhận diện đúng là Vietnamese; có lĩnh vực và danh sách thuật ngữ (xem TC12, TC13) | ✅ Tự động + thủ công |
| TC11 | Tài liệu tiếng Anh | Nhận diện "English" | `test_detector::test_language_detection` đạt | ✅ Tự động |
| TC12 | Tài liệu chuyên ngành ML | Domain = Deep Learning (hoặc Machine Learning), có hồ sơ chuyên ngành | Tự động: `test_pipeline_specialized` đạt (văn bản tổng hợp). Thủ công với giáo trình thật `d2l_3_4` (hồi quy softmax): lĩnh vực = **Mathematics (độ phủ từ khóa 49.0%)**; lĩnh vực gần nhất: Machine Learning, Deep Learning. **Kết quả không khớp kỳ vọng** | ❌ Không khớp trên tài liệu thật |
| TC13 | Danh sách thuật ngữ thô | Gộp biến thể hoa/thường, bỏ cụm quá dài | `test_term_cleaner` (6 test) đạt. Thủ công với `d2l_3_4`: giao diện báo 25 thuật ngữ sau lọc và gộp biến thể (số "trước khi lọc" hiển thị là 19). Danh sách còn lẫn tên riêng (Claude Shannon, Duncan Luce, Zhang), từ không phải thuật ngữ (Section, API) và cụm như "Softmax Trong Section"; giao diện tự ghi chú bộ lọc dựa trên luật đơn giản nên có thể bỏ sót hoặc giữ nhầm | 🟡 Một phần |
| TC14 | "Convolutional Neural Network (CNN)" | `CNN = Convolutional Neural Network`; không tự đoán khi không có định nghĩa | `test_abbreviation` (8 test) đạt | ✅ Tự động |
| TC15 | Bảng trong tài liệu | Giữ quan hệ hàng/cột | Chỉ đọc bảng thành hàng văn bản. Tóm tắt bảng: **chưa làm** | 🟡 Một phần |
| TC16 | Công thức `y = Wx + b` | Phát hiện và giữ nguyên | Phát hiện: `test_formulas` đạt (gồm test cho bộ lọc mã nguồn `looks_like_code`). Math OCR/ảnh công thức: **chưa làm** | 🟡 Một phần |
| TC17 | Tóm tắt | Baseline cho đúng số câu, giữ thứ tự; Gemini ra bản tóm tắt | Baseline: `test_baseline*` đạt. Thủ công: chế độ "Tóm tắt nhanh" với `gemini-flash-lite-latest` trả bản tóm tắt tiếng Việt 4 câu cho `d2l_3_4` (nội dung: hồi quy softmax, mã hóa một nóng, cross-entropy, vector hóa, accuracy) | ✅ Tự động + thủ công |
| TC18 | TTS | Sinh file mp3 từ bản tóm tắt | Thủ công: tùy chọn "Tạo audio ngay sau khi xử lý" tạo được audio, giọng HoaiMy (vi-VN), tốc độ bình thường, 572 ký tự; trình phát hiển thị thời lượng 00:32 | ✅ Thủ công |
| TC19 | Tải audio | Nút tải .mp3 hoạt động | Thủ công: bấm "Tải audio (.mp3)" ở tab Quản lý, tải được file mp3 và mở nghe được | ✅ Thủ công |
| TC20 | File `.xyz` | Báo định dạng chưa hỗ trợ | `test_loader::test_unsupported_extension` đạt | ✅ Tự động |
| TC21 | Tab Đánh giá với `d2l_3_4` | Hiển thị bảng độ đo cho từng phương pháp và kết quả kiểm chứng nội dung | Thủ công: TPR (giữ thuật ngữ) TextRank 16% (4/25), TextRank + thuật ngữ 20% (5/25), Gemini 40% (10/25); tỉ lệ nén 6.0% / 5.2% / 3.6%; từ/câu 50.5 / 43.8 / 30.8; NPR, UPR, FPR không có số liệu hoặc "không có". Kiểm chứng nội dung: không phát hiện dấu hiệu bất thường; điểm bám gốc trung bình 0.382 (ngưỡng báo 0.12) | ✅ Thủ công |

Test bổ sung đã có: kiểm chứng nội dung (`test_validator`, 7), độ đo mới (`test_metrics_specialized`, 6), thư viện bài học theo chủ sở hữu (`test_lesson_store`, `test_identity`), trình phát (`test_audio_player`), chế độ đọc toàn bộ (`test_reading_mode`), chuyển model dự phòng (`test_fallback_models`).

## Ghi chú giới hạn

- Các độ đo ở TC21 do đồ án tự định nghĩa, không phải benchmark chuẩn; kết quả chỉ là dấu hiệu nghi ngờ, cần đối chiếu với tài liệu gốc.
- Mỗi case thủ công chỉ chạy một lần, chưa lặp lại; các case TC10, 12, 13, 17, 18, 21 dùng tài liệu `d2l_3_4`.

## Chạy test

```powershell
pip install pytest
pytest -q
```