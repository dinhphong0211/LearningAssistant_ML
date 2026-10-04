# Test cases (mục XXXI của ThucHien.txt)

Cột **Actual Output** chỉ ghi kết quả đã thực sự chạy. Test tự động: chạy ngày 03/10/2026 trong môi trường không có mạng (125 test, 0 lỗi); lệnh chạy ở cuối tài liệu. Các case cần mạng/Gemini/TTS hoặc file thật **chưa chạy**, để trống cho bạn điền sau khi thử thủ công.

| ID | Input | Expected Output | Actual Output | Status |
|---|---|---|---|---|
| TC01 | PDF có text layer (`data/sample.pdf`) | Trích xuất được đoạn văn, không rỗng | Chưa có test tự động cho PDF | ⬜ Chưa chạy |
| TC02 | DOCX có đoạn và bảng | Giữ thứ tự, bảng thành hàng `a \| b` | `test_loader::test_docx_paragraphs_and_tables` đạt | ✅ Tự động |
| TC03 | PPTX có text, bảng, ghi chú | Có text từng slide và ghi chú, đúng số slide | `test_loader::test_pptx_text_notes_and_pages` đạt | ✅ Tự động |
| TC04 | TXT UTF-8 | Đọc đúng tiếng Việt, tách đoạn | `test_loader::test_txt_utf8` đạt | ✅ Tự động |
| TC05 | PNG/JPG | OCR trả văn bản | Mới thử với hàm OCR giả (`test_image_with_fake_ocr`); chưa thử Gemini thật | 🟡 Một phần |
| TC06 | PDF scan (không text layer) | Tự chuyển sang OCR, cảnh báo giới hạn 10 trang | Chưa chạy | ⬜ Chưa chạy |
| TC07 | File rỗng 0 byte | Báo lỗi tiếng Việt, không treo | `test_loader::test_empty_file` đạt | ✅ Tự động |
| TC08 | DOCX hỏng | `DocumentError` thân thiện | `test_loader::test_corrupted_docx` đạt | ✅ Tự động |
| TC09 | Tài liệu rất dài | Chia đoạn có overlap, map-reduce không vượt giới hạn | Chia đoạn: `test_chunker` đạt. Map-reduce với Gemini thật: chưa chạy | 🟡 Một phần |
| TC10 | Tài liệu tiếng Việt | Nhận diện ngôn ngữ, lĩnh vực, thuật ngữ | `test_pipeline_specialized::test_specialized_fields_present`, `test_detector::test_language_detection` đạt (dữ liệu tổng hợp) | ✅ Tự động |
| TC11 | Tài liệu tiếng Anh | Nhận diện "English" | `test_detector::test_language_detection` đạt | ✅ Tự động |
| TC12 | Tài liệu chuyên ngành ML | Domain = Deep Learning, có hồ sơ chuyên ngành | `test_pipeline_specialized` đạt (văn bản tổng hợp, chưa thử giáo trình thật) | 🟡 Một phần |
| TC13 | Danh sách thuật ngữ thô | Gộp biến thể hoa/thường, bỏ cụm quá dài | `test_term_cleaner` (6 test) đạt | ✅ Tự động |
| TC14 | "Convolutional Neural Network (CNN)" | `CNN = Convolutional Neural Network`; không tự đoán khi không có định nghĩa | `test_abbreviation` (8 test) đạt | ✅ Tự động |
| TC15 | Bảng trong tài liệu | Giữ quan hệ hàng/cột | Chỉ đọc bảng thành hàng văn bản. Tóm tắt bảng: **chưa làm** | 🟡 Một phần |
| TC16 | Công thức `y = Wx + b` | Phát hiện và giữ nguyên | Phát hiện: `test_formulas` đạt. Math OCR/ảnh công thức: **chưa làm** | 🟡 Một phần |
| TC17 | Tóm tắt | Baseline cho đúng số câu, giữ thứ tự; Gemini ra bản tóm tắt | Baseline: `test_baseline*` đạt. Gemini thật: chưa chạy | 🟡 Một phần |
| TC18 | TTS | Sinh file mp3 từ bản tóm tắt | Chưa chạy (cần mạng tới dịch vụ edge-tts) | ⬜ Chưa chạy |
| TC19 | Tải audio | Nút tải .mp3 hoạt động | Chưa thử trên giao diện | ⬜ Chưa chạy |
| TC20 | File `.xyz` | Báo định dạng chưa hỗ trợ | `test_loader::test_unsupported_extension` đạt | ✅ Tự động |

Test bổ sung đã có: kiểm chứng nội dung (`test_validator`, 7), độ đo mới (`test_metrics_specialized`, 6), thư viện bài học theo chủ sở hữu (`test_lesson_store`, `test_identity`), trình phát (`test_audio_player`), chế độ đọc toàn bộ (`test_reading_mode`), chuyển model dự phòng (`test_fallback_models`).

## Chạy test

```powershell
pip install pytest
pytest -q
```
