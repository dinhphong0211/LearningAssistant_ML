# Trợ Lý Học Tập Thông Minh

Đồ án môn Học máy: **Xây dựng trợ lý học tập sử dụng NLP và Machine Learning để đọc, tóm tắt và chuyển đổi tài liệu học tập chuyên ngành thành giọng nói.**

*An Intelligent Learning Assistant for Reading, Summarizing and Converting Specialized Educational Documents into Speech Using NLP and Machine Learning.*

> Tình trạng: phần mềm chạy được; **chưa có kết quả thực nghiệm**. Xem [docs/PROGRESS.md](docs/PROGRESS.md) để biết đã làm và chưa làm gì.

## Giới thiệu và bài toán

Sinh viên có nhiều tài liệu dài, nhiều thuật ngữ, công thức. Ứng dụng đọc tài liệu, tóm tắt (hoặc đọc toàn bộ), giữ nguyên thuật ngữ chuyên ngành, kiểm tra bản tóm tắt có dấu hiệu bịa không, rồi chuyển thành audio để nghe, kể cả khi tắt màn hình điện thoại.

## Tính năng

- Đọc PDF (có text, và PDF scan bằng OCR), DOCX, PPTX, TXT, PNG, JPG, JPEG.
- Ba chế độ: Tóm tắt nhanh, Study Notes, Đọc toàn bộ (bỏ số trang, header/footer, tác giả, mục lục).
- Phân tích chuyên ngành: lĩnh vực, thuật ngữ, từ viết tắt, công thức, đơn vị, Domain Profile.
- So sánh ba phương pháp: TextRank, TextRank + thuật ngữ, Gemini; độ đo TPR, NPR, UPR, FPR, tỉ lệ nén, ROUGE (khi có bản tham chiếu).
- Kiểm chứng nội dung bản tóm tắt (số, đơn vị, viết tắt, độ bám nội dung gốc).
- Chuyển thành giọng nói (edge-tts), trình phát tự lưu vị trí nghe, điều khiển trên màn hình khóa, hẹn giờ.
- Thư viện bài học riêng theo thiết bị.

## Xử lý tài liệu chuyên ngành

Phạm vi ưu tiên: Computer Science → AI → Machine Learning / Deep Learning / NLP. **Hệ thống không hiểu mọi tài liệu chuyên ngành**; ngoài phạm vi này kết quả không được đảm bảo. Mức hiện tại: đọc file + nhận diện thuật ngữ/viết tắt/công thức/đơn vị bằng luật. Chưa nhận diện cấu trúc chương/mục/bảng/hình.

## Kiến trúc

Xem [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (sơ đồ Mermaid).

## Công nghệ

Python, Streamlit, PyMuPDF, python-docx, python-pptx, Gemini API (`google-generativeai`), edge-tts, numpy. Không dùng GPU.

## Cài đặt (Windows, PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # rồi mở .env và điền GEMINI_API_KEY
streamlit run app/main.py
```

Không đưa `.env` hay khóa API lên GitHub. Trên Streamlit Community Cloud, đặt khóa trong *Settings → Secrets*.

## Sử dụng

1. Mở tab **➕ Bài mới**, tải tài liệu, chọn mức tóm tắt, bấm **Bắt đầu phân tích**.
2. Tab **🎧 Bài học**: nghe audio, đọc nội dung, xem thuật ngữ và hồ sơ chuyên ngành, xem đánh giá.
3. Tab **📚 Thư viện**: mở lại bài cũ và nghe tiếp đúng vị trí.

## Mô hình

- **Baseline:** TextRank tự cài đặt (`app/summarization/baseline.py`), không huấn luyện.
- **Mô hình chính:** Gemini, mô hình pretrained, **chỉ dùng để suy luận (inference), không huấn luyện hay fine-tune**. Thuật ngữ, viết tắt, công thức của tài liệu được thêm vào prompt (keyword-guided summarization).
- Chưa có mô hình do đồ án tự huấn luyện (xem [docs/PROGRESS.md](docs/PROGRESS.md) mục 4.1).

## Dataset

Chưa dùng dataset nào. Xem [data/README.md](data/README.md).

## Đánh giá

Công cụ đã có; **chưa chạy thực nghiệm nên không có bảng kết quả**. Các độ đo TPR/NPR/UPR/FPR/nén do đồ án tự định nghĩa, không phải benchmark chuẩn. ROUGE cài đặt thủ công trong `app/evaluation/metrics.py`.

## Cấu trúc thư mục

```
app/        main.py, pipeline.py, document/, preprocessing/, domain/, summarization/,
            evaluation/, tts/, utils/, lesson_store.py, identity.py, audio_player.py, ui_*.py
data/       README.md (mô tả dữ liệu), library.db (cục bộ, không đưa lên git)
docs/       PROGRESS.md, ARCHITECTURE.md, TEST_CASES.md, REFERENCES.md
tests/      test tự động (pytest)
```

## Chạy test

```powershell
pip install pytest
pytest -q
```

## Giới hạn

- Gemini là dịch vụ ngoài: có giới hạn lượt gọi, và nội dung tài liệu (đoạn gửi tóm tắt, ảnh khi OCR) được gửi tới Google.
- OCR bằng Gemini có thể đọc sai công thức, ký hiệu; PDF scan chỉ đọc 10 trang đầu.
- Kiểm chứng nội dung dựa trên trùng từ vựng nên không hiểu ngữ nghĩa; ngưỡng chưa hiệu chỉnh.
- Công thức dạng ảnh, bảng phức tạp chưa được xử lý.
- Vị trí nghe lưu theo trình duyệt; Streamlit Cloud xóa dữ liệu cục bộ khi khởi động lại nên thư viện có thể mất.
- Chưa kiểm chứng phát âm TTS cho thuật ngữ chuyên ngành.

## Hướng phát triển

Bộ phân loại lĩnh vực học máy; nhận diện cấu trúc tài liệu; thêm Key Concepts / Definitions / Exam Review; kiểm chứng bằng NLI; lưu trữ ngoài (Supabase) cho bản triển khai trên Cloud.

## Tài liệu tham khảo

Xem [docs/REFERENCES.md](docs/REFERENCES.md).
