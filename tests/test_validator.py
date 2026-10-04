from summarization.validator import validate_summary, grounding_scores
from summarization.baseline import split_sentences

SRC = (
    "Mạng nơ-ron tích chập (CNN) được huấn luyện bằng gradient descent trên tập dữ liệu CIFAR-10. "
    "Mô hình đạt độ chính xác 91 % sau 30 epoch. Quá trình huấn luyện dùng GPU với 16 GB bộ nhớ. "
    "Hàm mất mát cross-entropy được tối thiểu hóa trong mỗi vòng lặp. Overfitting được giảm bằng dropout. "
    "Tốc độ học ban đầu là 0.01 và giảm dần theo lịch trình. Kết quả cho thấy CNN vượt trội so với mạng truyền thẳng."
)


def test_faithful_summary_passes():
    s = "CNN được huấn luyện bằng gradient descent trên tập dữ liệu CIFAR-10 và đạt độ chính xác 91 %. Dropout giúp giảm overfitting."
    r = validate_summary(s, SRC, {"CNN": "Convolutional Neural Network"})
    assert not r["needs_review"] and r["issues"] == []


def test_fabricated_numbers_and_units_flagged():
    s = "Mô hình đạt độ chính xác 97 % khi huấn luyện trên 128 GB bộ nhớ."
    r = validate_summary(s, SRC)
    assert r["needs_review"]
    assert "97" in r["unsupported_numbers"] and "97 %" in r["unsupported_units"]


def test_abbreviation_conflict_flagged():
    src = "Artificial Intelligence (AI) là lĩnh vực rộng và AI ngày càng quan trọng trong đời sống."
    r = validate_summary("Ambient Interface (AI) là một khái niệm hoàn toàn khác.", src, {"AI": "Artificial Intelligence"})
    assert r["abbreviation_conflicts"] and r["needs_review"]


def test_unrelated_sentence_scores_lower_than_faithful_one():
    src_sents = split_sentences(SRC)
    faithful = split_sentences("Mô hình đạt độ chính xác 91 % sau 30 epoch.")
    unrelated = split_sentences("Công ty công bố kết quả kinh doanh quý ba vào tháng mười.")
    assert grounding_scores(faithful, src_sents)[0] > grounding_scores(unrelated, src_sents)[0]


def test_ungrounded_sentence_listed():
    s = "Công ty Google công bố kết quả kinh doanh quý ba vào tháng mười năm ngoái."
    r = validate_summary(s, SRC)
    assert r["ungrounded_sentences"] and r["ungrounded_sentences"][0]["score"] < r["threshold"]


def test_report_is_json_serializable():
    import json
    json.dumps(validate_summary("CNN đạt 91 % sau 30 epoch.", SRC))


def test_empty_summary():
    r = validate_summary("", SRC)
    assert r["n_sentences"] == 0 and not r["needs_review"]
