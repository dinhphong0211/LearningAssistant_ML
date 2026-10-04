from summarization.baseline import textrank_summarize

FILLER = [f"Câu số {i} nói về chủ đề chung của tài liệu này với nhiều chữ khác nhau." for i in range(8)]
TARGET = "Gradient descent cập nhật trọng số của mô hình học máy theo hướng giảm hàm mất mát."


def test_boost_pulls_in_sentence_with_terms():
    text = " ".join(FILLER + [TARGET])
    terms = ["gradient descent", "hàm mất mát"]
    plain = textrank_summarize(text, 2)
    assert TARGET not in plain
    # Hệ số mặc định (0.15) khá nhẹ nên ở đây dùng hệ số lớn để kiểm tra đúng cơ chế tăng điểm
    boosted = textrank_summarize(text, 2, boost_terms=terms, boost=10, max_boost=100)
    assert TARGET in boosted
    # Hệ số bằng 0 thì không có tác dụng
    assert textrank_summarize(text, 2, boost_terms=terms, boost=0) == plain


def test_no_terms_equals_plain():
    text = " ".join(FILLER + [TARGET])
    assert textrank_summarize(text, 3, boost_terms=[]) == textrank_summarize(text, 3)


def test_short_acronym_respects_word_boundary():
    text = " ".join(FILLER + ["Trail chạy rất xa trên con đường mòn dài và khó đi đến nơi."])
    # 'AI' không được khớp bên trong 'Trail'
    assert textrank_summarize(text, 2, boost_terms=["AI"]) == textrank_summarize(text, 2)
