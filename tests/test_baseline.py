from summarization.baseline import textrank_summarize, split_sentences

DOC = (
    "Học máy là một nhánh của trí tuệ nhân tạo cho phép máy tính học từ dữ liệu. "
    "Các thuật toán học máy xây dựng mô hình từ dữ liệu huấn luyện để dự đoán. "
    "Mạng nơ-ron là một mô hình học máy được lấy cảm hứng từ não người. "
    "Hôm nay trời nắng đẹp và tôi đi dạo trong công viên gần nhà. "
    "Dữ liệu huấn luyện chất lượng cao giúp mô hình học máy dự đoán chính xác hơn. "
    "Quả táo là một loại trái cây có vị ngọt và giàu vitamin cho cơ thể con người."
)


def test_returns_requested_number_of_sentences_in_original_order():
    out = textrank_summarize(DOC, n_sentences=3)
    sents = split_sentences(out)
    assert len(sents) == 3
    positions = [DOC.index(s) for s in sents]
    assert positions == sorted(positions)


def test_prefers_on_topic_sentences():
    out = textrank_summarize(DOC, n_sentences=3)
    assert "học máy" in out.lower()
    assert "Quả táo" not in out and "trời nắng" not in out


def test_short_text_returned_as_is():
    assert textrank_summarize("Một câu ngắn thôi nhé bạn.", n_sentences=3).startswith("Một câu")


def test_empty_text():
    assert textrank_summarize("", n_sentences=3) == ""
