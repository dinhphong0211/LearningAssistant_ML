# Nguồn tham khảo (mục XXXIII, XXXIV)

Quy ước: ✅ = đã mở và đối chiếu trang chính thức trong phiên làm việc ngày 03/10/2026; ⚠️ = tên bài, tác giả, năm tôi biết nhưng **chưa kiểm tra lại link**; hãy tra bằng tiêu đề trên arXiv hoặc ACL Anthology rồi điền link trước khi đưa vào báo cáo.

## Đã xác minh

| Tên | Tác giả | Năm | Dùng ở đâu | Link |
|---|---|---|---|---|
| TextRank: Bringing Order into Text (EMNLP 2004, trang 404–411) | Rada Mihalcea, Paul Tarau | 2004 | Baseline `summarization/baseline.py` (đồ thị câu, PageRank) | ✅ https://aclanthology.org/W04-3252/ |
| ROUGE: A Package for Automatic Evaluation of Summaries (Text Summarization Branches Out, trang 74–81) | Chin-Yew Lin | 2004 | `evaluation/metrics.py` (ROUGE-1/2/L cài đặt thủ công) | ✅ https://aclanthology.org/W04-1013/ |

## Cần xác minh link trước khi dùng

| Tên | Tác giả | Năm | Dùng ở đâu | Trạng thái |
|---|---|---|---|---|
| A Simple Algorithm for Identifying Abbreviation Definitions in Biomedical Text | Ariel S. Schwartz, Marti A. Hearst | 2003 | `domain/abbreviation.py` (ghép chữ cái viết tắt). Đây là bản **đơn giản hóa** của thuật toán. | ⚠️ |
| Attention Is All You Need | Vaswani và cộng sự | 2017 | Nền tảng Transformer (cơ sở lý thuyết chương 2) | ⚠️ |
| BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding | Devlin và cộng sự | 2018/2019 | Cơ sở lý thuyết | ⚠️ |
| BART: Denoising Sequence-to-Sequence Pre-training... | Lewis và cộng sự | 2019/2020 | Phương án tóm tắt abstractive thay thế (chưa dùng) | ⚠️ |
| Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer (T5) | Raffel và cộng sự | 2019/2020 | Phương án thay thế (chưa dùng) | ⚠️ |
| mT5: A Massively Multilingual Pre-trained Text-to-Text Transformer | Xue và cộng sự | 2020/2021 | Phương án đa ngôn ngữ cho tiếng Việt (chưa dùng) | ⚠️ |

## Tài liệu công nghệ cần tra (chưa tra)

Gemini API (google-generativeai), edge-tts, Streamlit, PyMuPDF, python-docx, python-pptx. Dùng trang tài liệu chính thức; ghi số phiên bản đang dùng (`pip freeze`) vào báo cáo.

## Không có nguồn

Các hệ số `boost=0.15`, `max_boost=0.6` (TextRank + thuật ngữ), ngưỡng bám nội dung gốc `0.12`, và các độ đo TPR/NPR/UPR/FPR **do đồ án tự định nghĩa**, chọn theo kinh nghiệm, chưa hiệu chỉnh trên dữ liệu thật.
