# Kiến trúc hệ thống

Sơ đồ Mermaid mô tả đúng code hiện tại. GitHub tự vẽ khối ` ```mermaid `. Các sơ đồ này **chưa được render thử** trong phiên làm việc; nếu GitHub báo lỗi cú pháp, dán vào https://mermaid.live để tìm dòng sai.

## 1. System Architecture

```mermaid
flowchart TD
    U["Người dùng (trình duyệt / điện thoại)"] --> UI["Streamlit UI: main.py, ui_theme.py, ui_panels.py"]
    UI --> ID["identity.py: mã thiết bị trong cookie"]
    UI --> UP["Tải file lên"]
    UP --> LD["document/loader.py: nhận diện định dạng và đọc"]
    LD --> OCR["document/ocr.py: OCR bằng Gemini (PDF scan, ảnh)"]
    LD --> PRE["preprocessing: chuẩn hóa Unicode, ghép khối, bỏ số trang/header/footer, chia đoạn"]
    PRE --> DOM["domain: lĩnh vực, thuật ngữ, viết tắt, công thức, đơn vị, Domain Profile"]
    DOM --> BASE["summarization/baseline.py: TextRank và TextRank + thuật ngữ"]
    DOM --> GEM["summarization/abstractive.py: Gemini map-reduce, có nhắc giữ thuật ngữ"]
    GEM --> VAL["summarization/validator.py: kiểm chứng nội dung"]
    BASE --> EVAL["evaluation: ROUGE, TPR, NPR, UPR, FPR, tỉ lệ nén"]
    VAL --> EVAL
    EVAL --> STORE["lesson_store.py: SQLite theo chủ sở hữu"]
    STORE --> TTS["tts/speech.py: chuẩn hóa văn bản, từ điển phát âm, edge-tts"]
    TTS --> PLAY["audio_player.py: phát, lưu vị trí nghe, nút màn hình khóa"]
    PLAY --> U
```

## 2. Data Flow (chế độ Tóm tắt)

```mermaid
flowchart LR
    A["File"] --> B["Danh sách đoạn văn"]
    B --> C["Văn bản đã chuẩn hóa"]
    C --> D["Thuật ngữ, viết tắt, công thức, đơn vị"]
    C --> E["Câu tóm tắt TextRank"]
    C --> F["Bản tóm tắt Gemini"]
    D --> F
    F --> G["Báo cáo kiểm chứng"]
    C --> G
    E --> H["Bảng độ đo"]
    F --> H
    D --> H
    F --> I["Văn bản đọc TTS"]
    I --> J["File mp3"]
    J --> K["Thư viện bài học"]
    F --> K
    G --> K
    H --> K
```

## 3. Sequence Diagram

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant UI as Streamlit
    participant P as pipeline.py
    participant G as Gemini API
    participant T as edge-tts
    participant S as SQLite
    U->>UI: Tải file, chọn mức tóm tắt
    UI->>P: run_pipeline(file, mode)
    P->>P: đọc file, chuẩn hóa, phân tích chuyên ngành
    P->>G: OCR (chỉ khi PDF scan hoặc ảnh)
    P->>P: TextRank và TextRank + thuật ngữ
    P->>G: tóm tắt từng đoạn rồi gộp (kèm danh sách thuật ngữ)
    G-->>P: bản tóm tắt
    P->>P: kiểm chứng và tính độ đo
    P-->>UI: kết quả
    UI->>S: lưu bài (theo mã thiết bị)
    UI->>T: tạo audio
    T-->>UI: mp3
    UI->>S: lưu audio
    UI-->>U: màn hình Bài học, trình phát
```

## 4. Component Diagram

```mermaid
flowchart TB
    subgraph app
        M["main.py"] --- UIP["ui_theme.py, ui_panels.py"]
        M --> PIPE["pipeline.py"]
        M --> STORE["lesson_store.py, identity.py"]
        M --> AP["audio_player.py"]
        PIPE --> DOC["document/"]
        PIPE --> PRE["preprocessing/"]
        PIPE --> DOMN["domain/"]
        PIPE --> SUM["summarization/"]
        PIPE --> EV["evaluation/"]
        M --> TTS["tts/"]
    end
    SUM --> GAPI["Gemini API (ngoài)"]
    DOC --> GAPI
    TTS --> EDGE["edge-tts (ngoài)"]
```

## 5. Phân biệt rule-based và học máy

| Thành phần | Kỹ thuật | Học máy? |
|---|---|---|
| Nhận diện lĩnh vực | Đếm từ khóa có ranh giới từ | Không |
| Thuật ngữ, viết tắt, công thức, đơn vị | Regex và luật | Không |
| Baseline | TF-IDF, cosine, PageRank (TextRank) | Có (không giám sát), không huấn luyện |
| Tóm tắt chính | Gemini pretrained, chỉ inference | Có, **không tự huấn luyện/fine-tune** |
| Kiểm chứng nội dung | Cosine TF-IDF trên cửa sổ 3 câu, so khớp số/đơn vị | Không |
| Bộ phân loại lĩnh vực học máy | (đề xuất, chưa làm) | Sẽ có, huấn luyện có giám sát |
