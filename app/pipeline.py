"""Pipeline xử lý tài liệu, tách khỏi giao diện để dễ test.

Luồng tóm tắt: đọc file -> chuẩn hóa -> nhận diện chuyên ngành -> thuật ngữ -> tóm tắt
(baseline TextRank + Gemini map-reduce) -> trả về dict kết quả.

Luồng "Đọc toàn bộ" (FULL_LABEL): đọc file (bỏ số trang, header/footer lặp lại) -> chuẩn hóa
giữ ranh giới đoạn -> nhận diện chuyên ngành -> Gemini chép lại nguyên văn, bỏ tác giả/mục lục.
Không có bước tóm tắt và không chạy baseline TextRank.
"""
import time

from document.loader import load_document, DocumentError
from document.ocr import make_gemini_ocr
from preprocessing.chunker import chunk_text, chunk_paragraphs
from preprocessing.boilerplate import drop_page_number_paragraphs
from preprocessing.text_normalizer import normalize_vietnamese_text
from domain.detector import detect_domain
from domain.terminology import extract_terminology
from domain.term_cleaner import clean_terms
from summarization.baseline import textrank_summarize
from summarization.abstractive import TransformerSummarizer, GEMINI_ERROR_PREFIX

STEPS = [
    "Đọc tài liệu",
    "Chuẩn hóa văn bản",
    "Nhận diện chuyên ngành và thuật ngữ",
    "Tóm tắt baseline (TextRank)",
    "Tóm tắt bằng Gemini",
]

STEPS_FULL = [
    "Đọc tài liệu và bỏ số trang, header, footer",
    "Chuẩn hóa văn bản",
    "Nhận diện chuyên ngành và thuật ngữ",
    "Làm sạch toàn văn bằng Gemini",
]

QUICK_LABEL = "Tóm tắt nhanh (Quick Summary)"
DETAIL_LABEL = "Chi tiết bài học (Study Notes - Hỗ trợ nghe)"
FULL_LABEL = "Đọc toàn bộ (không tóm tắt)"


def run_pipeline(path, summarizer, mode, progress=None, chunk_chars=6000, use_ai_cleanup=True):
    """progress(step_index, total_steps, label) được gọi trước mỗi bước (nếu có).

    use_ai_cleanup chỉ có tác dụng ở chế độ FULL_LABEL: False thì chỉ làm sạch bằng luật
    (không gọi Gemini, nhanh và không tốn hạn mức nhưng không bỏ được tên tác giả, mục lục).
    """
    if mode == FULL_LABEL:
        return _run_full_reading(path, summarizer, progress, chunk_chars, use_ai_cleanup)
    return _run_summary(path, summarizer, mode, progress, chunk_chars)


def _run_full_reading(path, summarizer, progress, chunk_chars, use_ai_cleanup):
    total = len(STEPS_FULL)
    timings = {}

    def step(i):
        if progress:
            progress(i, total, STEPS_FULL[i])
        return time.time()

    # 1. Đọc, bỏ số trang / header / footer ở mức cấu trúc file
    t = step(0)
    ocr = make_gemini_ocr(summarizer.model)
    doc = load_document(path, ocr_func=ocr, clean_page_furniture=True)
    timings["Đọc tài liệu"] = time.time() - t

    # 2. Chuẩn hóa, GIỮ ranh giới đoạn (chế độ tóm tắt nối hết thành một dòng)
    t = step(1)
    paragraphs = [normalize_vietnamese_text(p) for p in doc.paragraphs]
    paragraphs = drop_page_number_paragraphs([p for p in paragraphs if p])
    full_text = "\n\n".join(paragraphs).strip()
    if not full_text:
        raise DocumentError("Sau khi loại số trang và header/footer, tài liệu không còn nội dung để đọc.")
    timings["Chuẩn hóa"] = time.time() - t

    # 3. Chuyên ngành + thuật ngữ
    t = step(2)
    domain, confidence = detect_domain(full_text)
    raw_terms = extract_terminology(full_text)
    terms = clean_terms(raw_terms, full_text)
    timings["Chuyên ngành & thuật ngữ"] = time.time() - t

    # 4. Gemini chép lại nguyên văn (hoặc chỉ dùng luật)
    t = step(3)
    warnings = list(doc.warnings)
    report = None
    if use_ai_cleanup:
        text, report = summarizer.prepare_reading_text(full_text, chunk_chars=chunk_chars)
        if report["errors"] and report["ai"] + report["dropped"] == 0:
            # Không khối nào qua được Gemini: lỗi thật (API key, hết hạn mức...), báo cho người dùng
            text = f"{GEMINI_ERROR_PREFIX}: {report['errors'][0]}"
        elif report["kept_raw"]:
            warnings.append(
                f"{report['kept_raw']}/{report['chunks']} khối không qua được Gemini (lỗi hoặc Gemini rút gọn "
                "quá mức) nên giữ nguyên bản đã lọc bằng luật; các khối này có thể còn tên tác giả, mục lục."
            )
    else:
        # Cùng bước làm sạch ký tự markdown như đường Gemini để máy đọc không vấp
        text = TransformerSummarizer._clean_for_tts(full_text)
        warnings.append("Chưa dùng Gemini: chỉ bỏ số trang và header/footer, tên tác giả và mục lục vẫn còn.")
    timings["Gemini" if use_ai_cleanup else "Làm sạch bằng luật"] = time.time() - t

    return {
        "mode": "full",
        "domain": domain,
        "conf": confidence,
        "terms": terms,
        "raw_terms_count": len(raw_terms),
        "summary": text,          # giữ khóa 'summary' để các màn hình, audio và xuất file dùng chung
        "baseline": "",
        "full_text": full_text,   # văn bản sau khi lọc bằng luật, là đầu vào của Gemini
        "info": {
            "type": doc.source_type,
            "pages": doc.pages,
            "chars": len(full_text),
            "chunks": len(chunk_paragraphs(paragraphs, max_chars=chunk_chars)),
            "used_ocr": doc.used_ocr,
        },
        "reading_report": report,
        "warnings": warnings,
        "timings": timings,
        "audio": None,
    }


def _run_summary(path, summarizer, mode, progress, chunk_chars):
    total = len(STEPS)
    timings = {}

    def step(i):
        if progress:
            progress(i, total, STEPS[i])
        return time.time()

    # 1. Đọc
    t = step(0)
    ocr = make_gemini_ocr(summarizer.model)
    doc = load_document(path, ocr_func=ocr)
    timings["Đọc tài liệu"] = time.time() - t

    # 2. Chuẩn hóa
    t = step(1)
    full_text = " ".join(normalize_vietnamese_text(p) for p in doc.paragraphs).strip()
    timings["Chuẩn hóa"] = time.time() - t

    # 3. Chuyên ngành + thuật ngữ
    t = step(2)
    domain, confidence = detect_domain(full_text)
    raw_terms = extract_terminology(full_text)
    terms = clean_terms(raw_terms, full_text)
    timings["Chuyên ngành & thuật ngữ"] = time.time() - t

    # 4. Baseline
    t = step(3)
    quick = mode == QUICK_LABEL
    baseline = textrank_summarize(full_text, n_sentences=4 if quick else 10)
    timings["Baseline TextRank"] = time.time() - t

    # 5. Gemini
    t = step(4)
    detail_level = "quick" if quick else "detailed"
    summary = summarizer.summarize_map_reduce(full_text, detail_level=detail_level)
    timings["Gemini"] = time.time() - t

    return {
        "mode": "summary",
        "domain": domain,
        "conf": confidence,
        "terms": terms,
        "raw_terms_count": len(raw_terms),
        "summary": summary,
        "baseline": baseline,
        "full_text": full_text,
        "info": {
            "type": doc.source_type,
            "pages": doc.pages,
            "chars": len(full_text),
            "chunks": len(chunk_text(full_text, max_chars=chunk_chars)),
            "used_ocr": doc.used_ocr,
        },
        "warnings": doc.warnings,
        "timings": timings,
        "audio": None,
    }
