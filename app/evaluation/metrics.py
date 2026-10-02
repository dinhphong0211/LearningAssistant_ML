"""Các độ đo đánh giá bản tóm tắt.

ROUGE ở đây được cài đặt thủ công (F1 của ROUGE-1, ROUGE-2, ROUGE-L) với cách
tách từ đơn giản. Kết quả có thể lệch nhẹ so với thư viện chuẩn `rouge-score`,
nên khi ghi vào báo cáo hãy nêu rõ đây là bản cài đặt của đồ án.

TPR, NPR, compression ratio là độ đo do đồ án tự định nghĩa, KHÔNG phải benchmark chuẩn.
"""
import re
from collections import Counter

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def tokenize(text):
    return _TOKEN_RE.findall((text or "").lower())


def _ngrams(tokens, n):
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def _f1(overlap, pred_total, ref_total):
    if overlap == 0 or pred_total == 0 or ref_total == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    p = overlap / pred_total
    r = overlap / ref_total
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r)}


def rouge_n(prediction, reference, n=1):
    pred, ref = tokenize(prediction), tokenize(reference)
    pg, rg = _ngrams(pred, n), _ngrams(ref, n)
    overlap = sum((pg & rg).values())
    return _f1(overlap, sum(pg.values()), sum(rg.values()))


def _lcs_length(a, b):
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def rouge_l(prediction, reference):
    pred, ref = tokenize(prediction), tokenize(reference)
    return _f1(_lcs_length(pred, ref), len(pred), len(ref))


def rouge_all(prediction, reference):
    return {
        "ROUGE-1": rouge_n(prediction, reference, 1),
        "ROUGE-2": rouge_n(prediction, reference, 2),
        "ROUGE-L": rouge_l(prediction, reference),
    }


# ---------- Độ đo do đồ án định nghĩa (không cần bản tóm tắt tham chiếu) ----------
def terminology_preservation_rate(summary, terms):
    """TPR = số thuật ngữ xuất hiện trong summary / tổng số thuật ngữ.
    Với bản tóm tắt ngắn, TPR thấp là bình thường vì không thể giữ hết thuật ngữ."""
    terms = [t for t in terms if t and t.strip()]
    if not terms:
        return None
    low = (summary or "").lower()
    kept = [t for t in terms if t.lower() in low]
    return {"rate": len(kept) / len(terms), "kept": len(kept), "total": len(terms)}


def number_preservation_rate(summary, source):
    """NPR = tỉ lệ số trong summary cũng xuất hiện trong tài liệu gốc.
    Số trong summary mà gốc không có là dấu hiệu nghi ngờ hallucination."""
    sum_nums = _NUMBER_RE.findall(summary or "")
    if not sum_nums:
        return None
    src_nums = set(_NUMBER_RE.findall(source or ""))
    unsupported = sorted({n for n in sum_nums if n not in src_nums})
    supported = sum(1 for n in sum_nums if n in src_nums)
    return {
        "rate": supported / len(sum_nums),
        "total": len(sum_nums),
        "unsupported": unsupported,
    }


def compression_ratio(summary, source):
    s, d = len(tokenize(summary)), len(tokenize(source))
    return (s / d) if d else None
