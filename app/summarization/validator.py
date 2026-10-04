"""Kiểm chứng nội dung bản tóm tắt so với tài liệu gốc (SOURCE -> SUMMARY -> VALIDATION).

Đây là các kiểm tra heuristic để PHÁT HIỆN DẤU HIỆU nghi ngờ hallucination, không chứng minh
được bản tóm tắt đúng hay sai. Bốn kiểm tra:
  1. Số trong summary không có trong gốc            (NPR)
  2. Cặp 'số + đơn vị' trong summary không có trong gốc (UPR)
  3. Từ viết tắt được định nghĩa khác với tài liệu gốc
  4. Câu trong summary có độ tương đồng từ vựng thấp với mọi đoạn của gốc ("ungrounded"):
     cosine TF-IDF giữa câu summary và từng cửa sổ 3 câu liên tiếp của gốc, lấy giá trị lớn nhất.

Giới hạn quan trọng của kiểm tra 4:
  - Dựa trên trùng từ vựng, KHÔNG hiểu ngữ nghĩa. Tóm tắt diễn đạt lại bằng từ khác có thể bị
    báo nhầm (dương tính giả); câu sai nhưng dùng đúng từ của gốc lại lọt qua (âm tính giả).
  - Ngưỡng `grounding_threshold` chọn theo kinh nghiệm, cần hiệu chỉnh trên dữ liệu thật
    (đồ án chưa thực hiện) trước khi dùng để kết luận.
  - Nghiên cứu hướng chính xác hơn: NLI/entailment, QA-based consistency (xem docs/PROGRESS.md).
"""
import math
import re
from collections import Counter, defaultdict

from evaluation.metrics import number_preservation_rate, unit_preservation_rate
from domain.abbreviation import abbreviation_conflicts
from summarization.baseline import split_sentences, _tokens

DEFAULT_THRESHOLD = 0.12
WINDOW = 3


def _windows(sentences, size=WINDOW):
    if len(sentences) <= size:
        return [sentences] if sentences else []
    return [sentences[i:i + size] for i in range(len(sentences) - size + 1)]


def grounding_scores(summary_sentences, source_sentences, window=WINDOW):
    """Với mỗi câu summary: cosine TF-IDF lớn nhất tới một cửa sổ `window` câu của gốc (0..1)."""
    wins = _windows(source_sentences, window)
    docs = [Counter(t for s in w for t in _tokens(s)) for w in wins]
    n = len(docs)
    if n == 0:
        return [0.0 for _ in summary_sentences]
    df = Counter(t for d in docs for t in d)
    idf = lambda t: math.log((1 + n) / (1 + df.get(t, 0))) + 1.0

    index = defaultdict(list)
    norms = []
    for i, d in enumerate(docs):
        vec = {t: c * idf(t) for t, c in d.items()}
        norms.append(math.sqrt(sum(v * v for v in vec.values())) or 1.0)
        for t, v in vec.items():
            index[t].append((i, v))

    scores = []
    for s in summary_sentences:
        q = {t: c * idf(t) for t, c in Counter(_tokens(s)).items()}
        qnorm = math.sqrt(sum(v * v for v in q.values()))
        if not q or qnorm == 0:
            scores.append(1.0)          # không có từ nội dung để so (câu quá ngắn): không báo nghi ngờ
            continue
        dots = defaultdict(float)
        for t, qv in q.items():
            for i, v in index.get(t, ()):
                dots[i] += qv * v
        best = max((d / (qnorm * norms[i]) for i, d in dots.items()), default=0.0)
        scores.append(min(1.0, best))
    return scores


def validate_summary(summary, source, abbreviations=None, grounding_threshold=DEFAULT_THRESHOLD):
    """Trả về báo cáo kiểm chứng (dict thuần, lưu JSON được)."""
    npr = number_preservation_rate(summary, source)
    upr = unit_preservation_rate(summary, source)
    conflicts = abbreviation_conflicts(summary, abbreviations or {})

    sum_sents = split_sentences(summary)
    src_sents = split_sentences(source)
    ungrounded, mean = [], None
    if sum_sents and src_sents:
        scores = grounding_scores(sum_sents, src_sents)
        mean = sum(scores) / len(scores)
        ungrounded = [
            {"sentence": s, "score": round(sc, 3)}
            for s, sc in zip(sum_sents, scores) if sc < grounding_threshold
        ]

    issues = []
    if npr and npr["unsupported"]:
        issues.append("Số không có trong tài liệu gốc: " + ", ".join(npr["unsupported"]))
    if upr and upr["unsupported"]:
        issues.append("Số kèm đơn vị không có trong tài liệu gốc: " + ", ".join(upr["unsupported"]))
    for c in conflicts:
        issues.append(f"Từ viết tắt {c['abbreviation']} bị định nghĩa khác gốc: '{c['summary']}' (gốc: '{c['source']}')")
    if ungrounded:
        issues.append(f"{len(ungrounded)} câu ít bám vào nội dung gốc (có thể là diễn đạt lại, cần đối chiếu)")

    return {
        "unsupported_numbers": npr["unsupported"] if npr else [],
        "unsupported_units": upr["unsupported"] if upr else [],
        "abbreviation_conflicts": conflicts,
        "ungrounded_sentences": ungrounded,
        "n_sentences": len(sum_sents),
        "grounding_mean": round(mean, 3) if mean is not None else None,
        "threshold": grounding_threshold,
        "needs_review": bool(issues),
        "issues": issues,
    }
