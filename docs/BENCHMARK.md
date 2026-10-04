# Chạy thực nghiệm (Phase 10)

Script `scripts/run_benchmark.py` so TextRank, TextRank + thuật ngữ và Gemini trên một thư mục tài liệu, xuất CSV để đưa vào báo cáo. Số liệu thật của lần chạy đã thực hiện nằm trong `results/` (xem mục 3) và được phân tích ở chương 5 của báo cáo. Tài liệu này chỉ mô tả cách chạy và cách đọc kết quả.

## 1. Chuẩn bị dữ liệu

Đặt vào `data/benchmark/` theo quy ước tên:

```
data/benchmark/
  d2l_3_1.txt        tài liệu (PDF, DOCX, PPTX hoặc TXT)
  d2l_3_1.ref.txt    phần "Tóm tắt" cuối mục trong sách D2L tiếng Việt: do tác giả sách viết
                     bằng tiếng Anh, bản tiếng Việt là bản dịch của nhóm dịch, KHÔNG phải do người làm đồ án viết
  d2l_3_4.txt, d2l_3_4.ref.txt
  d2l_4_1.txt, d2l_4_1.ref.txt
```

Nguồn và giấy phép: xem `data/README.md`. Ba mục dùng ở đây là 3.1 (Hồi quy tuyến tính), 3.4 (Hồi quy Softmax) và 4.1 (Multilayer Perceptrons) của *Dive into Deep Learning* bản tiếng Việt. File không có `.ref.txt` vẫn chạy nhưng bỏ qua ROUGE.

## 2. Chạy

```powershell
# Chỉ TextRank, chạy offline, không tốn lượt gọi API
python scripts/run_benchmark.py --sentences 3

# Thêm Gemini (cần GEMINI_API_KEY trong .env). Cắt Gemini còn 3 câu đầu để so công bằng với TextRank
python scripts/run_benchmark.py --gemini --sentences 3 --truncate-gemini --delay 5

# Thử nhanh với 2 tài liệu đầu
python scripts/run_benchmark.py --gemini --limit 2
```

## 3. Kết quả

Ghi vào `results/` (mỗi lần chạy có dấu thời gian):

| File | Nội dung |
|---|---|
| `benchmark_<giờ>.csv` | Mỗi hàng một cặp (tài liệu, phương pháp): số từ, ROUGE-1/2/L F1, TPR, NPR, UPR, FPR, tỉ lệ nén, từ/câu, cờ cần kiểm tra |
| `benchmark_<giờ>_summary.csv` | Trung bình theo phương pháp; các cột `*_n` cho biết có bao nhiêu tài liệu thực sự tham gia mỗi trung bình (ô trống bị bỏ qua) |
| `run_info_<giờ>.json` | Ngày giờ, số tài liệu, tài liệu lỗi, tham số, model Gemini, phiên bản Python |
| `summaries/` | Văn bản tóm tắt từng phương pháp, để bạn đọc và chấm tay |

File CSV dùng mã hóa `utf-8-sig` nên mở bằng Excel đọc đúng tiếng Việt.

## 4. Cách đọc kết quả cho đúng

1. **Kiểm tra cột `words` trước.** Nếu Gemini dài gấp nhiều lần TextRank thì ROUGE không so được. Dùng `--truncate-gemini`, và ghi rõ trong báo cáo là đã cắt.
2. Tham chiếu của SciTLDR và XL-Sum chỉ 1 đến 2 câu, nên ROUGE tuyệt đối thấp. Chỉ so **giữa các phương pháp với nhau**, đừng so với con số trong bài báo gốc.
3. ROUGE ở đây do app tự cài đặt, có thể lệch nhẹ so với thư viện chuẩn. TPR, NPR, UPR, FPR do đồ án tự định nghĩa.
4. Với vài chục tài liệu, mọi chênh lệch nhỏ đều có thể do ngẫu nhiên. Đừng viết "phương pháp A tốt hơn B" nếu chỉ hơn vài phần trăm trên ít tài liệu; hãy viết đúng những gì số liệu cho thấy và nêu cỡ mẫu.
5. Ngoài số liệu, hãy đọc tay thư mục `summaries/` ít nhất cho vài tài liệu và ghi nhận xét định tính (đúng ý, thiếu ý, bịa ý).
6. Nếu TPR của "TextRank + thuật ngữ" gần bằng TextRank thường, nghĩa là bộ thuật ngữ ít tác động trên dữ liệu đó; đó vẫn là kết quả hợp lệ để báo cáo.

## 5. Giới hạn đã biết

- Thuật ngữ nhận diện bằng luật và từ điển khoảng 130 mục (ML, DL, NLP, Software, Math). Tài liệu ngoài các lĩnh vực này có ít thuật ngữ hơn thực tế, làm TPR kém ý nghĩa.
- Chưa OCR: PDF scan và ảnh sẽ được ghi vào danh sách lỗi của `run_info_*.json`.
- Gemini là dịch vụ ngoài, kết quả có thể thay đổi giữa các lần chạy. Nếu muốn lặp lại để lấy trung bình, hãy chạy nhiều lần và ghi rõ.
