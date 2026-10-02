"""Pipeline xử lý tài liệu, tách khỏi giao diện để dễ test.

Luồng: đọc file -> chuẩn hóa -> nhận diện chuyên ngành -> thuật ngữ -> tóm tắt
(baseline TextRank + Gemini map-reduce) -> trả về dict kết quả.
"""
import time

from document.loader import load_document
from document.ocr import make_gemini_ocr
from preprocessing.chunker import chunk_text
from preprocessing.text_normalizer import normalize_vietnamese_text
from domain.detector import detect_domain
from domain.terminology import extract_terminology
from domain.term_cleaner import clean_terms
from summarization.baseline import textrank_summarize

STEPS = [
    "Đọc tài liệu",
    "Chuẩn hóa văn bản",
    "Nhận diện chuyên ngành và thuật ngữ",
    "Tóm tắt baseline (TextRank)",
    "Tóm tắt bằng Gemini",
]

QUICK_LABEL = "Tóm tắt nhanh (Quick Summary)"


def run_pipeline(path, summarizer, mode, progress=None, chunk_chars=6000):
    """progress(step_index, total_steps, label) được gọi trước mỗi bước (nếu có)."""
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
