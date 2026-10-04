# Đánh giá tiến độ đồ án

Cập nhật: 03/10/2026. Đối chiếu với `ThucHien.txt` (mục XL Roadmap và mục L Checklist cuối cùng).

Chú giải: ✅ đã xong · 🟡 làm một phần · ❌ chưa làm.

## 1. Nhận định chung

- **Phần phần mềm đã vượt mức MVP** của đồ án: đọc 7 định dạng, OCR, tóm tắt baseline và Gemini, kiểm chứng nội dung, TTS, trình phát nghe lại được vị trí, thư viện bài học. Checklist cuối: 16 ✅ / 11 🟡 / 7 ❌ trên 34 mục. Roadmap: 7 ✅ / 8 🟡 / 2 ❌ trên 17 phase.
- **Phần học thuật gần như chưa có**: chưa chạy thực nghiệm nào, chưa có dataset, báo cáo, slide. Với đồ án *môn Học máy*, đây là phần quyết định điểm, và là phần cần làm tiếp.
- **Machine Learning nằm ở đâu hiện nay (nói đúng sự thật):** TextRank (xếp hạng đồ thị không giám sát trên vector TF-IDF) và Gemini (mô hình pretrained, chỉ inference). Đồ án **chưa huấn luyện hay fine-tune mô hình nào**. Nếu giảng viên hỏi "bạn train gì?", câu trả lời hiện tại là "chưa". Xem mục 4 để biết cách khắc phục.

## 2. Checklist cuối (mục L)

| # | Hạng mục | Trạng thái | Ghi chú |
|---|---|---|---|
| 1 | Source code chạy được | ✅ | Chạy local và trên Streamlit Cloud (bạn đã xác nhận). 125/125 test tự động đạt trong môi trường không có mạng. |
| 2 | README | 🟡 | Đã có bản nháp (`README.md`), còn thiếu ảnh chụp màn hình và số liệu đánh giá thật. |
| 3 | requirements.txt | 🟡 | Không ghim phiên bản (từng gây ImportError trên Cloud khi lệch phiên bản). `rouge-score` và `pypdf` có trong file nhưng không có dòng code nào import. |
| 4 | PDF support | ✅ | PyMuPDF, ghép khối văn bản, bỏ số trang/header/footer ở chế độ đọc toàn bộ. |
| 5 | DOCX support | ✅ | python-docx, giữ thứ tự đoạn và bảng (bảng đọc thành hàng `a | b`). |
| 6 | PPTX support | ✅ | python-pptx, đọc cả bảng và ghi chú diễn giả. |
| 7 | TXT support | ✅ | Thử nhiều bảng mã (UTF-8, UTF-16, cp1258, cp1252). |
| 8 | OCR | 🟡 | OCR bằng Gemini, không phải Tesseract; chỉ 10 trang đầu của PDF scan; chưa test PDF scan thật; chưa đo độ chính xác. |
| 9 | Specialized document | 🟡 | Mới ở giữa Level 1 và Level 3: có thuật ngữ, viết tắt, công thức, đơn vị. CHƯA có Level 2 (cấu trúc heading/section/bảng). |
| 10 | Domain detection | 🟡 | Đếm từ khóa cho 5 lĩnh vực (ML, DL, NLP, Software, Math). Chưa so sánh với TF-IDF + bộ phân loại, zero-shot hay embedding. |
| 11 | Terminology handling | 🟡 | Luật regex + lọc heuristic. Chưa dùng NER/embedding. Bộ mẫu ban đầu thiên về Laravel/web. |
| 12 | Abbreviation handling | ✅ | Mới thêm: thuật toán ghép chữ cái kiểu Schwartz-Hearst, phát hiện xung đột trong bản tóm tắt. Không nhận định nghĩa tiếng Việt. |
| 13 | Long document | ✅ | Chia đoạn có overlap + map-reduce. Chưa thử tài liệu hàng trăm trang. |
| 14 | Baseline | ✅ | TextRank tự cài bằng numpy, thêm biến thể tăng điểm theo thuật ngữ (domain-aware). |
| 15 | Transformer/model | 🟡 | Dùng Gemini (pretrained, chỉ inference). Không phải BART/T5/mT5 trên Hugging Face, không fine-tune. Phải trình bày đúng như vậy trong báo cáo. |
| 16 | Evaluation | 🟡 | Code và giao diện đủ (ROUGE, TPR, NPR, UPR, FPR, nén, kiểm chứng). CHƯA chạy thực nghiệm nào: chưa có tập tài liệu, chưa có bản tóm tắt tham chiếu, chưa có bảng kết quả. |
| 17 | TTS | ✅ | edge-tts + chuẩn hóa văn bản + từ điển phát âm. Chưa kiểm chứng phát âm thuật ngữ bằng tai. |
| 18 | Audio player | ✅ | Trình phát tự viết: lưu vị trí nghe, nút màn hình khóa, tua 15 giây, tốc độ, hẹn giờ. |
| 19 | Download audio | ✅ | Tải .mp3 ở tab Quản lý. |
| 20 | UI | ✅ | 3 màn hình, thư viện riêng theo thiết bị, giao diện cho điện thoại. |
| 21 | Error handling | 🟡 | Có DocumentError tiếng Việt, thử lại và chuyển model khi lỗi 429. Chưa lập bảng NGUYÊN NHÂN → PHÁT HIỆN → CÁCH XỬ LÝ → THÔNG BÁO. |
| 22 | Testing | 🟡 | 125 test tự động. Chưa chạy các test case thủ công (PDF thật, PDF scan, Gemini thật, TTS, tải audio). Xem `docs/TEST_CASES.md`. |
| 23 | Architecture diagram | ✅ | Bản nháp Mermaid trong `docs/ARCHITECTURE.md` (chưa render thử trên GitHub). |
| 24 | Data flow | ✅ | Bản nháp Mermaid trong `docs/ARCHITECTURE.md`. |
| 25 | Report | ❌ | Chưa viết. Cần số liệu thực nghiệm trước. |
| 26 | Slide | ❌ | Chưa làm. |
| 27 | Demo | ❌ | Chưa chuẩn bị tài liệu demo và kịch bản chạy thử. |
| 28 | References | 🟡 | `docs/REFERENCES.md`: 2 nguồn đã xác minh link, các nguồn còn lại ghi rõ chưa xác minh. |
| 29 | Dataset source | ❌ | Chưa có. Đồ án chưa dùng và chưa chọn tập dữ liệu nào. |
| 30 | License | ❌ | Chưa chọn giấy phép. Đây là quyết định của bạn (ví dụ MIT). |
| 31 | No API key in source | ✅ | Quét mã nguồn không thấy khóa. Cần tự kiểm tra thêm lịch sử git (`git log -p -S AIza`). |
| 32 | .gitignore | ✅ | Đã chặn .env, venv, outputs, *.mp3, data/library.db. |
| 33 | Source zip | ❌ | Chưa đóng gói theo mẫu MSSV_HoTen_DAMH_Src.zip. |
| 34 | Data share link | ❌ | Chưa có dữ liệu để chia sẻ. |

## 3. Roadmap theo phase (mục XL)

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| Phase 0 — Phân tích bài toán | 🟡 | Chưa có tài liệu Phase 0 chính thức (problem statement, phạm vi, yêu cầu). Cần viết cho báo cáo chương 1 và 3. |
| Phase 1 — Nghiên cứu | 🟡 | Mới có `docs/REFERENCES.md` khởi đầu. Chưa có bảng so sánh phương pháp (extractive vs abstractive, các TTS...). |
| Phase 2 — Môi trường | ✅ | Python, venv, `.env`, Dev Container, Streamlit Cloud. |
| Phase 3 — Xử lý tài liệu | ✅ | 7 định dạng. |
| Phase 4 — OCR | 🟡 | Gemini OCR; chưa đánh giá. |
| Phase 5 — Tiền xử lý | ✅ | Chuẩn hóa Unicode, ghép khối, bỏ số trang/header/footer, chia đoạn có overlap. |
| Phase 6 — Nhận diện lĩnh vực | 🟡 | Từ khóa; thiếu so sánh phương pháp. |
| Phase 7 — Thuật ngữ | 🟡 | Luật/heuristic + viết tắt + công thức + đơn vị. |
| Phase 8 — Baseline | ✅ | TextRank + biến thể domain-aware. |
| Phase 9 — Tóm tắt Transformer | 🟡 | Gemini inference; chưa có mô hình tự huấn luyện/fine-tune. |
| Phase 10 — Đánh giá | 🟡 | Công cụ đã sẵn sàng, chưa chạy thực nghiệm. |
| Phase 11 — TTS | ✅ | Chưa kiểm chứng phát âm. |
| Phase 12 — Giao diện | ✅ |  |
| Phase 13 — Tích hợp | ✅ |  |
| Phase 14 — Kiểm thử | 🟡 | Test tự động tốt, test thủ công chưa chạy. |
| Phase 15 — Báo cáo | ❌ |  |
| Phase 16 — Trình bày | ❌ |  |

## 4. Khoảng trống lớn nhất và đề xuất

### 4.1. Chưa có thành phần học máy thật (ưu tiên cao nhất)
Đề xuất khả thi nhất: **bộ phân loại lĩnh vực học máy** (TF-IDF + Logistic Regression hoặc Naive Bayes) thay/so sánh với bộ đếm từ khóa hiện tại. Cần một tập văn bản có nhãn lĩnh vực, chia train/validation/test, báo cáo accuracy/F1 và ma trận nhầm lẫn. Nguồn dữ liệu cần chọn và kiểm tra giấy phép; **chưa xác minh** nguồn nào (xem `data/README.md`). Khi có rồi, đây là chỗ bạn trả lời được "Machine Learning nằm ở đâu" bằng số liệu của chính mình.

### 4.2. Chưa có thực nghiệm đánh giá
Công cụ đã sẵn sàng. Cần: 5 đến 10 tài liệu thật (ưu tiên giáo trình/slide ML-AI), mỗi tài liệu một bản tóm tắt tham chiếu do bạn tự viết (không dùng AI), rồi chạy TextRank, TextRank + thuật ngữ và Gemini, ghi lại ROUGE, TPR, NPR, UPR, FPR. **Không điền số liệu khi chưa chạy.**

### 4.3. Chưa hiểu cấu trúc tài liệu (Level 2)
Hiện tài liệu là danh sách đoạn. Chưa nhận diện heading/section/bảng/hình/caption. Hướng đơn giản: dùng kích thước font và đậm của PyMuPDF để suy ra heading, DOCX dùng style `Heading n`. Nếu không kịp, ghi rõ vào phần Giới hạn của báo cáo.

### 4.4. Các loại summary mới có 2 trên 9
Có Quick và Study Notes (+ chế độ đọc toàn bộ). Thiếu Key Concepts, Key Terms, Definitions, Formulas, Exam Review. Hai mục đầu gần như miễn phí vì đã có `profile` (khái niệm chính, thuật ngữ, công thức).

### 4.5. Dọn mã thừa
Các file sau không được import ở đâu cả và gây nhầm lẫn khi báo cáo: `app/summarization/extractive.py` (cần nltk, scikit-learn, networkx không có trong requirements; ý tưởng đã nằm trong `baseline.py`), `app/document/image_reader.py` (Tesseract, đường dẫn Windows cứng, `pytesseract` không có trong requirements), `app/pdf_reader.py` (script thử nghiệm). Lệnh gỡ ở cuối tài liệu này.

### 4.6. Quyền riêng tư
`ThucHien.txt` (mục XXX) yêu cầu không lưu nội dung tài liệu nếu không cần. Từ bản này, app ở hai chế độ tóm tắt **mặc định không lưu văn bản gốc** (chỉ lưu bản tóm tắt và kết quả đánh giá tính sẵn); có ô tick để bật lưu. Chế độ Đọc toàn bộ vẫn giữ văn bản vì bản đọc chính là nội dung đó. Lưu ý: bản tóm tắt vẫn được lưu, và nội dung ảnh/PDF scan vẫn được gửi cho Gemini (Google) khi OCR. Thư viện tách theo thiết bị bằng cookie, không phải tài khoản (xem `app/identity.py`).

## 5. Rủi ro khi bảo vệ

| Câu hỏi dễ gặp | Trả lời trung thực |
|---|---|
| Bạn có train model không? | Chưa. Dùng Gemini pretrained (inference) và TextRank không giám sát. Phần học máy tự làm: (sau khi làm 4.1) bộ phân loại lĩnh vực. |
| Sao không dùng BART/T5/mT5? | Gemini cho tiếng Việt tốt hơn mà không cần GPU. Đổi lại là phụ thuộc API, giới hạn lượt gọi, nội dung gửi ra ngoài. |
| Làm sao biết tóm tắt không bịa? | Có kiểm tra heuristic (số, đơn vị, viết tắt, bám nội dung gốc) nhưng không chứng minh được; ngưỡng chưa hiệu chỉnh. |
| TTS có đọc đúng thuật ngữ không? | Có từ điển phát âm, nhưng chưa kiểm chứng bằng tai trên tập thuật ngữ nào. |
| Hệ thống hiểu mọi tài liệu chuyên ngành? | Không. Tập trung CS/AI/ML/DL/NLP; ngoài phạm vi này kết quả không được đảm bảo. |

## 6. Lệnh dọn mã thừa (tùy chọn)

```powershell
git rm app/summarization/extractive.py app/document/image_reader.py app/pdf_reader.py
```
