from evaluation.metrics import unit_preservation_rate, formula_preservation_rate, avg_sentence_length
from evaluation.report import evaluate_summaries


def test_upr_detects_unsupported_unit():
    r = unit_preservation_rate("Đạt 91 % trên 32 GB.", "Mô hình đạt 91 % với 16 GB.")
    assert r["unsupported"] == ["32 GB"] and r["rate"] == 0.5


def test_upr_none_without_units():
    assert unit_preservation_rate("Không có số liệu.", "Gốc cũng vậy.") is None


def test_fpr_ignores_whitespace():
    r = formula_preservation_rate("Công thức y=Wx+b rất phổ biến.", ["y = Wx + b", "E = mc^2"])
    assert r == {"rate": 0.5, "kept": 1, "total": 2}


def test_fpr_none_without_formulas():
    assert formula_preservation_rate("bất kỳ", []) is None


def test_avg_sentence_length():
    assert avg_sentence_length("Một hai ba. Bốn năm sáu bảy.") == 3.5
    assert avg_sentence_length("") is None


def test_evaluate_summaries_structure():
    out = evaluate_summaries({"A": "Đạt 91 % rồi."}, "Mô hình đạt 91 % ở thí nghiệm.", ["Mô hình"], ["y = x"])
    assert set(out["A"]) == {"tpr", "npr", "upr", "fpr", "compression", "avg_sentence_words"}
