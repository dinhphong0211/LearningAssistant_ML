from evaluation.metrics import (
    rouge_n, rouge_l, rouge_all,
    terminology_preservation_rate, number_preservation_rate, compression_ratio,
)


def test_rouge_identical_text_is_one():
    r = rouge_all("học máy là một nhánh của AI", "học máy là một nhánh của AI")
    assert all(abs(v["f1"] - 1.0) < 1e-9 for v in r.values())


def test_rouge_disjoint_is_zero():
    assert rouge_n("alpha beta", "gamma delta", 1)["f1"] == 0.0


def test_rouge1_known_value():
    # pred: 4 từ, ref: 4 từ, trùng 2 -> P = R = 0.5 -> F1 = 0.5
    r = rouge_n("a b c d", "a b x y", 1)
    assert abs(r["f1"] - 0.5) < 1e-9


def test_rouge_l_uses_subsequence():
    # LCS của "a b c d" và "a x c d" = 3 (a, c, d)
    r = rouge_l("a b c d", "a x c d")
    assert abs(r["f1"] - 0.75) < 1e-9


def test_tpr():
    r = terminology_preservation_rate("Sprint và Scrum Master", ["Sprint", "Scrum Master", "Backlog"])
    assert r["kept"] == 2 and r["total"] == 3


def test_npr_detects_unsupported_number():
    r = number_preservation_rate("Sprint kéo dài 4 tuần, họp 15 phút", "Sprint kéo dài 4 tuần, họp 15 phút")
    assert r["rate"] == 1.0
    r = number_preservation_rate("Sprint kéo dài 16 giờ", "Sprint kéo dài 8 giờ")
    assert r["unsupported"] == ["16"] and r["rate"] == 0.0


def test_npr_none_when_no_numbers():
    assert number_preservation_rate("không có số", "gốc 5") is None


def test_compression_ratio():
    assert abs(compression_ratio("a b", "a b c d") - 0.5) < 1e-9
