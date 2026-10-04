"""Chạy thực nghiệm hàng loạt: so TextRank, TextRank + thuật ngữ và (tùy chọn) Gemini trên một thư mục tài liệu.

Cấu trúc thư mục đầu vào (mặc định data/benchmark/):
    bai01.pdf          tài liệu (PDF, DOCX, PPTX, TXT)
    bai01.ref.txt      bản tóm tắt tham chiếu DO NGƯỜI VIẾT (không dùng AI) cho bai01
    bai02.txt
    bai02.ref.txt

Chạy (PowerShell, trong thư mục gốc project):
    python scripts/run_benchmark.py                       # chỉ TextRank, chạy offline, không tốn API
    python scripts/run_benchmark.py --gemini              # thêm Gemini (cần GEMINI_API_KEY trong .env)
    python scripts/run_benchmark.py --gemini --sentences 2 --truncate-gemini --delay 5

Kết quả ghi vào results/ (CSV chi tiết, CSV trung bình theo phương pháp, các bản tóm tắt, run_info.json).

Cách đọc kết quả công bằng:
  - Mọi phương pháp nên có độ dài gần nhau. `--sentences N` đặt số câu cho TextRank; Gemini không điều khiển
    được số câu nên dùng thêm `--truncate-gemini` (cắt còn N câu đầu, được ghi rõ trong tên phương pháp).
  - Cột `words` cho biết độ dài thật; hãy kiểm tra trước khi so ROUGE.
  - ROUGE được cài đặt thủ công trong app/evaluation/metrics.py nên có thể lệch nhẹ so với thư viện chuẩn.
  - Số tài liệu nhỏ thì chỉ là minh họa, không kết luận thống kê.
"""
import argparse
import csv
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from document.loader import load_document, SUPPORTED_EXTENSIONS, get_extension   # noqa: E402
from preprocessing.text_normalizer import normalize_vietnamese_text               # noqa: E402
from domain.terminology import extract_terminology                                # noqa: E402
from domain.term_cleaner import clean_terms                                       # noqa: E402
from domain.lexicon import add_lexicon_terms                                      # noqa: E402
from summarization.baseline import textrank_summarize, split_sentences            # noqa: E402
from summarization.validator import validate_summary                              # noqa: E402
from evaluation.metrics import rouge_all                                          # noqa: E402
from evaluation.report import evaluate_summaries                                  # noqa: E402
from pipeline import analyze_specialized, glossary_guide, with_guidance           # noqa: E402

METHOD_TEXTRANK = "TextRank"
METHOD_TEXTRANK_TERMS = "TextRank + thuật ngữ"
METHOD_GEMINI = "Gemini"

FIELDS = [
    "doc", "method", "words", "compression", "rouge1_f1", "rouge2_f1", "rougeL_f1",
    "tpr", "npr", "upr", "fpr", "avg_sentence_words", "needs_review", "n_issues", "has_reference",
]
NUMERIC = [f for f in FIELDS if f not in ("doc", "method", "has_reference")]


def find_cases(folder):
    """[(đường dẫn tài liệu, đường dẫn tham chiếu hoặc None)], bỏ qua file .ref.txt và định dạng lạ."""
    cases = []
    for p in sorted(Path(folder).iterdir()):
        if not p.is_file() or p.name.lower().endswith(".ref.txt"):
            continue
        if get_extension(str(p)) not in SUPPORTED_EXTENSIONS:
            continue
        ref = p.with_name(p.stem + ".ref.txt")
        cases.append((p, ref if ref.exists() else None))
    return cases


def prepare(path):
    doc = load_document(str(path))   # không OCR: PDF scan/ảnh sẽ báo lỗi và bị ghi vào danh sách lỗi
    paragraphs = [normalize_vietnamese_text(p) for p in doc.paragraphs]
    full_text = " ".join(paragraphs).strip()
    terms = add_lexicon_terms(clean_terms(extract_terminology(full_text), full_text), full_text)
    abbreviations, formulas, units, profile = analyze_specialized(paragraphs, full_text, terms)
    return {
        "text": full_text, "terms": terms, "abbreviations": abbreviations,
        "formulas": formulas, "units": units, "profile": profile,
    }


def _truncate(text, n):
    return " ".join(split_sentences(text)[:n])


def summarize_all(prep, n_sentences, summarizer=None, detail="quick", truncate_gemini=False):
    out = {
        METHOD_TEXTRANK: textrank_summarize(prep["text"], n_sentences=n_sentences),
        METHOD_TEXTRANK_TERMS: textrank_summarize(prep["text"], n_sentences=n_sentences, boost_terms=prep["terms"]),
    }
    if summarizer is not None:
        guided = with_guidance(summarizer, glossary_guide(prep["terms"], prep["abbreviations"], prep["formulas"]))
        text = guided.summarize_map_reduce(prep["text"], detail_level=detail)
        if truncate_gemini:
            out[f"{METHOD_GEMINI} (cắt {n_sentences} câu)"] = _truncate(text, n_sentences)
        else:
            out[METHOD_GEMINI] = text
    return out


def _rate(d):
    return None if not d else round(d["rate"], 4)


def score_methods(doc_name, summaries, prep, reference):
    metrics = evaluate_summaries(summaries, prep["text"], prep["terms"], prep["formulas"])
    rows = []
    for method, text in summaries.items():
        m = metrics[method]
        validation = validate_summary(text, prep["text"], prep["abbreviations"])
        row = {
            "doc": doc_name, "method": method, "words": len(text.split()),
            "compression": None if m["compression"] is None else round(m["compression"], 4),
            "tpr": _rate(m["tpr"]), "npr": _rate(m["npr"]), "upr": _rate(m["upr"]), "fpr": _rate(m["fpr"]),
            "avg_sentence_words": None if m["avg_sentence_words"] is None else round(m["avg_sentence_words"], 2),
            "needs_review": int(validation["needs_review"]), "n_issues": len(validation["issues"]),
            "has_reference": int(bool(reference)),
            "rouge1_f1": None, "rouge2_f1": None, "rougeL_f1": None,
        }
        if reference:
            r = rouge_all(text, reference)
            row["rouge1_f1"] = round(r["ROUGE-1"]["f1"], 4)
            row["rouge2_f1"] = round(r["ROUGE-2"]["f1"], 4)
            row["rougeL_f1"] = round(r["ROUGE-L"]["f1"], 4)
        rows.append(row)
    return rows


def summarize_rows(rows):
    """Trung bình từng độ đo theo phương pháp (bỏ qua ô trống). Kèm số tài liệu tham gia."""
    out = []
    for method in dict.fromkeys(r["method"] for r in rows):
        group = [r for r in rows if r["method"] == method]
        item = {"method": method, "n_docs": len(group)}
        for f in NUMERIC:
            vals = [r[f] for r in group if r.get(f) is not None]
            item[f] = round(statistics.mean(vals), 4) if vals else None
            item[f + "_n"] = len(vals)
        out.append(item)
    return out


def _write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig để Excel mở đúng tiếng Việt
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})


def run_benchmark(folder, out_dir, n_sentences=3, summarizer=None, detail="quick",
                  truncate_gemini=False, delay=0.0, limit=None, log=print):
    folder, out_dir = Path(folder), Path(out_dir)
    cases = find_cases(folder)
    if limit:
        cases = cases[:limit]
    if not cases:
        raise SystemExit(f"Không thấy tài liệu hỗ trợ trong {folder}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (out_dir / "summaries").mkdir(parents=True, exist_ok=True)
    rows, errors = [], []
    for i, (path, ref_path) in enumerate(cases, 1):
        log(f"[{i}/{len(cases)}] {path.name}" + ("" if ref_path else "  (không có .ref.txt: bỏ qua ROUGE)"))
        try:
            prep = prepare(path)
            if not prep["text"]:
                raise ValueError("tài liệu không có văn bản")
            reference = ref_path.read_text(encoding="utf-8").strip() if ref_path else None
            summaries = summarize_all(prep, n_sentences, summarizer, detail, truncate_gemini)
            rows.extend(score_methods(path.stem, summaries, prep, reference))
            for method, text in summaries.items():
                safe = "".join(c if c.isalnum() else "_" for c in method)
                (out_dir / "summaries" / f"{path.stem}.{safe}.txt").write_text(text, encoding="utf-8")
        except Exception as e:   # một tài liệu lỗi không làm hỏng cả lượt chạy
            errors.append({"doc": path.name, "error": f"{type(e).__name__}: {e}"})
            log(f"    LỖI: {e}")
        if summarizer is not None and delay and i < len(cases):
            time.sleep(delay)

    summary = summarize_rows(rows)
    detail_path = out_dir / f"benchmark_{stamp}.csv"
    summary_path = out_dir / f"benchmark_{stamp}_summary.csv"
    _write_csv(detail_path, rows, FIELDS)
    _write_csv(summary_path, summary, ["method", "n_docs"] + [x for f in NUMERIC for x in (f, f + "_n")])
    info = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "folder": str(folder), "n_docs_found": len(cases), "n_docs_ok": len({r["doc"] for r in rows}),
        "errors": errors, "sentences": n_sentences, "gemini": summarizer is not None,
        "gemini_model": getattr(summarizer, "model_name", None) if summarizer is not None else None,
        "detail": detail, "truncate_gemini": truncate_gemini, "python": platform.python_version(),
    }
    (out_dir / f"run_info_{stamp}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"rows": rows, "summary": summary, "errors": errors, "detail_csv": detail_path,
            "summary_csv": summary_path, "info": info}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", default=str(ROOT / "data" / "benchmark"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--sentences", type=int, default=3, help="số câu của TextRank (mặc định 3)")
    ap.add_argument("--gemini", action="store_true", help="chạy thêm Gemini (cần API key, tốn lượt gọi)")
    ap.add_argument("--model", default=None, help="tên model Gemini (mặc định theo .env hoặc tự chọn)")
    ap.add_argument("--detail", choices=("quick", "detailed"), default="quick")
    ap.add_argument("--truncate-gemini", action="store_true", help="cắt bản Gemini còn N câu đầu để so công bằng")
    ap.add_argument("--delay", type=float, default=3.0, help="giây nghỉ giữa các tài liệu khi dùng Gemini")
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N tài liệu đầu (để thử)")
    args = ap.parse_args(argv)

    summarizer = None
    if args.gemini:
        from summarization.abstractive import TransformerSummarizer
        summarizer = TransformerSummarizer(args.model)

    result = run_benchmark(args.folder, args.out, args.sentences, summarizer, args.detail,
                           args.truncate_gemini, args.delay, args.limit)
    print("\nTrung bình theo phương pháp:")
    for s in result["summary"]:
        print(f"  {s['method']:<32} n={s['n_docs']:<3} từ={s['words']}  R1={s['rouge1_f1']}  R2={s['rouge2_f1']}  "
              f"RL={s['rougeL_f1']}  TPR={s['tpr']}  NPR={s['npr']}")
    print(f"\nChi tiết: {result['detail_csv']}\nTrung bình: {result['summary_csv']}")
    if result["errors"]:
        print(f"{len(result['errors'])} tài liệu lỗi, xem run_info_*.json")


if __name__ == "__main__":
    main()
