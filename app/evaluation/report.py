"""Gom các độ đo không cần bản tham chiếu cho nhiều bản tóm tắt vào một dict (dễ lưu JSON, dễ test).

Tất cả độ đo ở đây do đồ án tự định nghĩa (xem metrics.py), không phải benchmark chuẩn.
"""
from evaluation.metrics import (
    terminology_preservation_rate,
    number_preservation_rate,
    unit_preservation_rate,
    formula_preservation_rate,
    compression_ratio,
    avg_sentence_length,
)


def evaluate_summaries(summaries, source, terms=None, formulas=None):
    """summaries: {tên phương pháp: văn bản}. Trả về {tên: {tpr, npr, upr, fpr, compression, avg_sentence_words}}."""
    out = {}
    for name, text in summaries.items():
        out[name] = {
            "tpr": terminology_preservation_rate(text, terms or []),
            "npr": number_preservation_rate(text, source),
            "upr": unit_preservation_rate(text, source),
            "fpr": formula_preservation_rate(text, formulas or []),
            "compression": compression_ratio(text, source),
            "avg_sentence_words": avg_sentence_length(text),
        }
    return out
